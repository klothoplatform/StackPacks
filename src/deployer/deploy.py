import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

from aiomultiprocess import Pool
from pulumi import automation as auto

from src.dependencies.injection import (
    get_binary_storage,
    get_iac_storage,
    get_pulumi_state_bucket_name,
    get_ses_client,
)
from src.deployer.models.pulumi_stack import PulumiStack
from src.deployer.models.util import (
    abort_workflow_run,
    complete_workflow_run,
    start_workflow_run,
)
from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import WorkflowRun, WorkflowRunStatus
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.pulumi.manager import AppManager, LiveState
from src.engine_service.binaries.fetcher import Binary
from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.project import StackPack, get_app_name, get_stack_packs
from src.project.actions import run_actions
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from src.util.aws.ses import AppData, send_deployment_success_email
from src.util.compress import zip_directory_recurse
from src.util.logging import logger
from src.util.tmp import TempDir


@dataclass
class DeploymentResult:
    manager: AppManager | None
    status: WorkflowJobStatus
    reason: str
    stack: PulumiStack | None


class StackDeploymentRequest(NamedTuple):
    workflow_job: WorkflowJob
    pulumi_config: dict[str, str]
    outputs: dict[str, str] = {}


PROJECT_NAME = "StackPack"


async def build_and_deploy(
    deployment_job: WorkflowJob,
    region: str,
    assume_role_arn: str,
    pulumi_config: dict[str, str],
    app_dir: Path,
    external_id: Optional[str] = None,
) -> DeploymentResult:
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    user = deployment_job.initiated_by
    run_id = deployment_job.partition_key

    pulumi_stack = PulumiStack(
        project_name=project_id,
        name=PulumiStack.sanitize_stack_name(app_id),
        status=WorkflowJobStatus.IN_PROGRESS.value,
        status_reason="Deployment in progress",
        created_by=user,
    )
    logger.info(
        f"Building {project_id}/{app_id}, deployment id {deployment_job.composite_key()}"
    )

    try:
        pulumi_stack.save()
        deployment_job.update(
            actions=[
                WorkflowJob.iac_stack_composite_key.set(pulumi_stack.composite_key()),
            ]
        )
        builder = AppBuilder(app_dir, get_pulumi_state_bucket_name())
        stack = builder.prepare_stack(pulumi_stack)
        builder.configure_aws(stack, region, assume_role_arn, external_id)
        for k, v in pulumi_config.items():
            stack.set_config(k, auto.ConfigValue(v, secret=True))
        deployer = AppDeployer(
            stack,
            DeploymentDir(project_id, run_id),
        )
        logger.info(
            f"Deploying {project_id}/{app_id}, deployment id {deployment_job.composite_key()}"
        )
        result_status, reason = await deployer.deploy()
        pulumi_stack.update(
            actions=[
                PulumiStack.status.set(result_status.value),
                PulumiStack.status_reason.set(reason),
            ]
        )
        deployment_job.update(
            actions=[
                WorkflowJob.status.set(result_status.value),
                WorkflowJob.status_reason.set(reason),
                WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
            ]
        )
        return DeploymentResult(
            manager=AppManager(stack),
            status=result_status,
            reason=reason,
            stack=pulumi_stack,
        )
    except Exception as e:
        logger.error(
            f"Error deploying {app_id} for project {project_id}: {e}", exc_info=True
        )
        pulumi_stack.update(
            actions=[
                PulumiStack.status.set(WorkflowJobStatus.FAILED.value),
                PulumiStack.status_reason.set(str(e)),
            ]
        )
        deployment_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.FAILED.value),
                WorkflowJob.status_reason.set(str(e)),
            ]
        )
        return DeploymentResult(
            manager=None,
            status=WorkflowJobStatus.FAILED,
            reason="Internal error",
            stack=None,
        )


async def build_and_deploy_application(
    deployment_job: WorkflowJob,
    imports: list,
    pulumi_config: dict[str, str],
    outputs: dict[str, str],
    tmp_dir: Path,
) -> DeploymentResult:
    job_composite_key = deployment_job.composite_key()
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    app_dir = tmp_dir / app_id
    iac_storage = get_iac_storage()
    binary_storage = get_binary_storage()
    project = Project.get(project_id)
    app = AppDeployment.get(
        project_id,
        AppDeployment.compose_range_key(app_id=app_id, version=project.apps[app_id]),
    )
    stack_packs = get_stack_packs()
    if app_id in stack_packs:
        stack_pack = stack_packs[app_id]
    else:
        stack_pack = CommonStack(
            stack_packs=[stack_packs[a] for a in project.apps if a in stack_packs],
            features=project.features,
        )

    logger.info(f"Running {project_id}/{app_id}, deployment id {job_composite_key}")
    engine_result = await app.run_app(
        stack_pack=stack_pack,
        app_dir=app_dir,
        binary_storage=binary_storage,
        imports=imports,
    )

    binary_storage.ensure_binary(Binary.IAC)
    await export_iac(
        ExportIacRequest(
            input_graph=engine_result.resources_yaml,
            name=project_id,
            tmp_dir=app_dir,
        )
    )
    stack_pack.copy_files(app.get_configurations(), app_dir)
    iac_bytes = zip_directory_recurse(BytesIO(), app_dir)
    logger.info(f"Writing IAC for {app_id} version {app.version()}")
    iac_storage.write_iac(project_id, app_id, app.version(), iac_bytes)

    deployment_job.update(
        actions=[
            WorkflowJob.status.set(WorkflowJobStatus.IN_PROGRESS.value),
            WorkflowJob.status_reason.set("Deployment in progress"),
            WorkflowJob.initiated_at.set(datetime.now(timezone.utc)),
        ]
    )
    app.transition_status(
        WorkflowJobStatus.IN_PROGRESS, WorkflowJobType.DEPLOY, "Deployment in progress"
    )
    result = await build_and_deploy(
        deployment_job=deployment_job,
        region=project.region,
        assume_role_arn=project.assumed_role_arn,
        pulumi_config=pulumi_config,
        app_dir=app_dir,
        external_id=project.assumed_role_external_id,
    )
    job_composite_key = deployment_job.composite_key()
    iac_composite_key = result.stack.composite_key() if result.stack else None
    logger.info(f"mapping outputs: {outputs}")
    try:
        stack_outputs = result.manager.get_outputs(outputs) if result.manager else {}
    except Exception as e:
        logger.error(f"Error getting outputs for {app_id}: {e}", exc_info=True)
        stack_outputs = {}
    logger.info(
        f"Deployment of {app.app_id()} complete. Status: {result.status}, with outputs: {stack_outputs}"
    )
    app.update(
        actions=[
            AppDeployment.outputs.set(stack_outputs),
            AppDeployment.iac_stack_composite_key.set(iac_composite_key),
            AppDeployment.deployments.add({job_composite_key}),
        ]
    )
    app.transition_status(result.status, WorkflowJobType.DEPLOY, result.reason)
    deployment_job.update(
        actions=[
            WorkflowJob.outputs.set(
                {
                    **(deployment_job.outputs or {}),
                    **(stack_outputs or {}),
                }
            ),
        ]
    )
    return result


async def run_concurrent_deployments(
    stacks: list[StackDeploymentRequest],
    imports: list,
    tmp_dir: Path,
) -> Tuple[list[str], tuple[DeploymentResult]]:
    # This version of the function creates an empty list tasks, then iterates over the stacks list.
    # For each stack, it applies the build_and_deploy function using the pool, awaits the result, and appends it to the tasks list.
    # This way, each task is awaited individually in an async context.

    logger.info(f"Running {len(stacks)} deployments")

    async with Pool() as pool:
        tasks = []
        app_order = []
        for stack in stacks:
            task = pool.apply(
                build_and_deploy_application,
                kwds=dict(
                    deployment_job=stack.workflow_job,
                    imports=imports,
                    pulumi_config=stack.pulumi_config,
                    outputs=stack.outputs,
                    tmp_dir=tmp_dir / stack.workflow_job.owning_app_id(),
                ),
            )
            app_order.append(stack.workflow_job.modified_app_id)
            tasks.append(task)

        gathered = await asyncio.gather(*tasks)
        logger.info(f"Tasks: {tasks}")
        return app_order, gathered


async def deploy_applications(
    deployment_jobs: List[WorkflowJob],
    imports: list,
    tmp_dir: Path,
    project: Project,
    live_state: LiveState,
) -> bool:
    sps = get_stack_packs()
    deployment_stacks: list[StackDeploymentRequest] = []
    apps: dict[str, AppDeployment] = {}

    for job in deployment_jobs:
        app_id = job.modified_app_id
        if app_id == Project.COMMON_APP_NAME:
            continue  # Common stack is deployed separately
        app = AppDeployment.get_latest_version(
            project_id=job.project_id(), app_id=app_id
        )
        apps[app.app_id()] = app
        sp = sps[app.app_id()]
        try:
            actions = sp.get_actions(app.get_configurations())
            run_actions(actions, project, live_state)
            pulumi_config = sp.get_pulumi_configs(app.get_configurations())
            outputs = {k: v.value_string() for k, v in sp.outputs.items()}
            deployment_stacks.append(
                StackDeploymentRequest(
                    workflow_job=job,
                    pulumi_config=pulumi_config,
                    outputs=outputs,
                )
            )
        except Exception as e:
            app.transition_status(
                WorkflowJobStatus.FAILED,
                WorkflowJobType.DEPLOY,
                "Could not run pre deploy actions",
            )

    order, results = await run_concurrent_deployments(
        stacks=deployment_stacks,
        imports=imports,
        tmp_dir=tmp_dir,
    )
    return all(result.status == WorkflowJobStatus.SUCCEEDED for result in results)


async def deploy_app(
    deployment_job: WorkflowJob,
    app: AppDeployment,
    stack_pack: StackPack,
    tmp_dir: Path,
    imports: list = [],
) -> DeploymentResult:
    pulumi_config = stack_pack.get_pulumi_configs(app.get_configurations())
    outputs = {k: v.value_string() for k, v in stack_pack.outputs.items()}
    _, results = await run_concurrent_deployments(
        [
            StackDeploymentRequest(
                workflow_job=deployment_job,
                pulumi_config=pulumi_config,
                outputs=outputs,
            )
        ],
        imports=imports,
        tmp_dir=tmp_dir,
    )

    return results[0]


async def execute_deployment_workflow(
    run: WorkflowRun,
):
    stack_packs = get_stack_packs()
    project_id = run.project_id
    with TempDir() as tmp_dir:
        logger.info(f"Deploying project {run.project_id}")
        binary_storage = get_binary_storage()
        project = Project.get(run.project_id)
        if project.destroy_in_progress:
            raise ValueError("Pack is currently being torn down")

        common_version = project.apps.get(Project.COMMON_APP_NAME, 0)
        if common_version == 0:
            raise ValueError("Common stack not found")

        common_app = AppDeployment.get(
            project_id,
            AppDeployment.compose_range_key(
                app_id=Project.COMMON_APP_NAME, version=common_version
            ),
        )
        common_stack = CommonStack(list(stack_packs.values()), project.features)
        apps: list[AppDeployment] = []

        for app_name, version in project.apps.items():
            if app_name == Project.COMMON_APP_NAME:
                continue
            app = AppDeployment.get(
                project_id,
                AppDeployment.compose_range_key(app_id=app_name, version=version),
            )
            apps.append(app)
            app.update(
                actions=[
                    AppDeployment.status.set(AppLifecycleStatus.PENDING.value),
                    AppDeployment.status_reason.set(
                        f"Updating Common Resources, then deploying {app_name}."
                    ),
                ]
            )

        try:
            logger.info(f"Deploying common stack")
            binary_storage.ensure_binary(Binary.IAC)

            # Create deploy jobs for each app
            deploy_common_job = WorkflowJob.create_job(
                WorkflowJob.compose_partition_key(
                    project_id=project_id,
                    workflow_type=WorkflowJobType.DEPLOY.value,
                    owning_app_id=None,
                    run_number=run.run_number(),
                ),
                job_type=WorkflowJobType.DEPLOY,
                modified_app_id=Project.COMMON_APP_NAME,
                initiated_by=run.initiated_by,
            )

            deploy_app_jobs = []
            for app_name, _ in project.apps.items():
                if app_name == Project.COMMON_APP_NAME:
                    continue
                deploy_app_jobs.append(
                    WorkflowJob.create_job(
                        WorkflowJob.compose_partition_key(
                            project_id=project_id,
                            workflow_type=WorkflowJobType.DEPLOY.value,
                            run_number=run.run_number(),
                            owning_app_id=None,
                        ),
                        job_type=WorkflowJobType.DEPLOY,
                        modified_app_id=app_name,
                        initiated_by=run.initiated_by,
                        dependencies=[deploy_common_job.composite_key()],
                    )
                )

            start_workflow_run(run)

            result = await deploy_app(
                deployment_job=deploy_common_job,
                app=common_app,
                stack_pack=common_stack,
                tmp_dir=tmp_dir,
            )
            if result.status == WorkflowJobStatus.FAILED:
                run.update(
                    actions=[
                        WorkflowRun.status.set(WorkflowRunStatus.FAILED.value),
                        WorkflowRun.status_reason.set(
                            f"{get_app_name(Project.COMMON_APP_NAME)} failed to deploy: {result.reason}"
                        ),
                    ]
                )
                for app in apps:
                    app.transition_status(
                        WorkflowJobStatus.FAILED, WorkflowJobType.DEPLOY, result.reason
                    )
                abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
                return

            live_state = await result.manager.read_deployed_state(tmp_dir)

            logger.info(f"Deploying app stacks")
            email = run.notification_email
            success = await deploy_applications(
                deployment_jobs=deploy_app_jobs,
                imports=live_state.to_constraints(
                    common_stack, common_app.configuration
                ),
                tmp_dir=tmp_dir,
                project=project,
                live_state=live_state,
            )
            complete_workflow_run(run)

            if success:
                if run.notification_email is not None:
                    app_data = [
                        AppData(
                            app_name=app.display_name or app.app_id(),
                            login_url=app.outputs.get("URL"),
                        )
                        for app in apps
                    ]
                    send_deployment_success_email(get_ses_client(), email, app_data)
        except Exception as e:
            abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
            for app_name, version in project.apps.items():
                if app_name == Project.COMMON_APP_NAME:
                    continue
                app = AppDeployment.get(
                    project_id,
                    AppDeployment.compose_range_key(app_id=app_name, version=version),
                )
                if app.status == AppLifecycleStatus.PENDING.value:
                    app.transition_status(
                        WorkflowJobStatus.FAILED, WorkflowJobType.DEPLOY, str(e)
                    )
            logger.error(f"Error deploying project {project_id}: {e}")
            raise e


async def execute_deploy_single_workflow(
    run: WorkflowRun,
):
    project_id = run.project_id
    app_id = run.app_id()
    project = Project.get(project_id)
    app = AppDeployment.get(
        project_id,
        AppDeployment.compose_range_key(app_id=app_id, version=project.apps[app_id]),
    )
    stackpacks = get_stack_packs()
    binary_storage = get_binary_storage()
    stack_pack = stackpacks[app.app_id()]
    common_stack = CommonStack(list(stackpacks.values()), project.features)
    common_app = AppDeployment.get(
        project_id,
        AppDeployment.compose_range_key(
            app_id=Project.COMMON_APP_NAME,
            version=project.apps[Project.COMMON_APP_NAME],
        ),
    )

    deploy_common_job = WorkflowJob.create_job(
        WorkflowJob.compose_partition_key(
            project_id=project_id,
            workflow_type=WorkflowJobType.DEPLOY.value,
            owning_app_id=app_id,
            run_number=run.run_number(),
        ),
        job_type=WorkflowJobType.DEPLOY,
        modified_app_id=Project.COMMON_APP_NAME,
        initiated_by=run.initiated_by,
    )
    deploy_app_job = WorkflowJob.create_job(
        WorkflowJob.compose_partition_key(
            project_id=project_id,
            workflow_type=WorkflowJobType.DEPLOY.value,
            owning_app_id=app_id,
            run_number=run.run_number(),
        ),
        job_type=WorkflowJobType.DEPLOY,
        modified_app_id=app_id,
        initiated_by=run.initiated_by,
        dependencies=[deploy_common_job.composite_key()],
    )

    start_workflow_run(run)

    app.update(
        actions=[
            AppDeployment.status.set(AppLifecycleStatus.PENDING.value),
            AppDeployment.status_reason.set(
                f"Updating Common Resources, then deploying {app.app_id()}."
            ),
        ]
    )
    try:
        binary_storage.ensure_binary(Binary.IAC)

        deploy_common_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.PENDING.value),
                WorkflowJob.status_reason.set("Deployment is pending"),
            ]
        )
        with TempDir() as tmp_dir:
            result = await deploy_app(
                deployment_job=deploy_common_job,
                app=common_app,
                stack_pack=common_stack,
                tmp_dir=tmp_dir,
            )
            if result.status == WorkflowJobStatus.FAILED:
                app.transition_status(
                    result.status, WorkflowJobType.DEPLOY, result.reason
                )
                abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
                return
            live_state = await result.manager.read_deployed_state(tmp_dir)
            constraints = live_state.to_constraints(
                common_stack, common_app.get_configurations()
            )

            actions = stack_pack.get_actions(app.get_configurations())
            run_actions(actions, project, live_state)
            await deploy_app(
                deployment_job=deploy_app_job,
                app=app,
                stack_pack=stack_pack,
                tmp_dir=tmp_dir,
                imports=constraints,
            )
            complete_workflow_run(run)
            if run.notification_email is not None:
                app_data = [
                    AppData(
                        app_name=app.display_name or app.app_id(),
                        login_url=app.outputs.get("URL", None) if app.outputs else None,
                    )
                ]
                send_deployment_success_email(
                    get_ses_client(), run.notification_email, app_data
                )
    except Exception as e:
        logger.error(f"Error deploying {app.app_id()}: {e}", exc_info=True)
        abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
        if app.status == AppLifecycleStatus.PENDING.value:
            app.transition_status(
                WorkflowJobStatus.FAILED, WorkflowJobType.DEPLOY, str(e)
            )
