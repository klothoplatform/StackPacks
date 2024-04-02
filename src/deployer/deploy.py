import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

from aiomultiprocess import Pool
from pulumi import automation as auto

from src.dependencies.injection import (
    get_binary_storage,
    get_iac_storage,
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
from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.stack_pack import ConfigValues, StackPack, get_app_name, get_stack_packs
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.stack_pack.models.project import Project
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.aws.ses import AppData, send_deployment_success_email
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
    iac: bytes,
    pulumi_config: dict[str, str],
    tmp_dir: Path,
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

    try:
        pulumi_stack.save()
        deployment_job.update(
            actions=[
                WorkflowJob.iac_stack_composite_key.set(pulumi_stack.composite_key()),
            ]
        )
        builder = AppBuilder(tmp_dir / app_id)
        stack = builder.prepare_stack(iac, pulumi_stack)
        builder.configure_aws(stack, region, assume_role_arn, external_id)
        for k, v in pulumi_config.items():
            stack.set_config(k, auto.ConfigValue(v, secret=True))
        deployer = AppDeployer(
            stack,
            DeploymentDir(project_id, run_id),
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
    except Exception:
        logger.error(f"Error deploying {app_id}", exc_info=True)
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
    pulumi_config: dict[str, str],
    outputs: dict[str, str],
    tmp_dir: Path,
) -> DeploymentResult:
    job_composite_key = deployment_job.composite_key()
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    logger.info(
        f"Building and deploying {app_id} for project {project_id} with deployment id {job_composite_key}"
    )
    iac_storage = get_iac_storage()
    project = Project.get(project_id)
    app = AppDeployment.get(
        project_id,
        AppDeployment.compose_range_key(app_id=app_id, version=project.apps[app_id]),
    )
    iac = iac_storage.get_iac(project.id, app.app_id(), project.apps[app.app_id()])
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
        iac=iac,
        pulumi_config=pulumi_config,
        tmp_dir=tmp_dir / app.app_id(),
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


async def rerun_pack_with_live_state(
    project: Project,
    common_pack: AppDeployment,
    common_stack: CommonStack,
    iac_storage: IacStorage,
    binary_storage: BinaryStorage,
    live_state: LiveState,
    sps: dict[str, StackPack],
    tmp_dir: str,
):
    logger.info(f"Rerunning project {project.id} with imports")

    configuration: dict[str, ConfigValues] = {}
    for name, version in project.apps.items():
        if name == Project.COMMON_APP_NAME:
            continue
        app = AppDeployment.get(
            project.id, AppDeployment.compose_range_key(app_id=name, version=version)
        )
        configuration[name] = app.get_configurations()

    await project.run_pack(
        stack_packs=sps,
        config=configuration,
        tmp_dir=tmp_dir,
        iac_storage=iac_storage,
        binary_storage=binary_storage,
        increment_versions=False,
        imports=live_state.to_constraints(common_stack, common_pack.configuration),
    )


async def deploy_applications(
    deployment_jobs: List[WorkflowJob],
    tmp_dir: Path,
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
        apps[app.get_app_id()] = app
        sp = sps[app.get_app_id()]
        pulumi_config = sp.get_pulumi_configs(app.get_configurations())
        outputs = {k: v.value_string() for k, v in sp.outputs.items()}
        deployment_stacks.append(
            StackDeploymentRequest(
                workflow_job=job,
                pulumi_config=pulumi_config,
                outputs=outputs,
            )
        )

    order, results = await run_concurrent_deployments(
        stacks=deployment_stacks,
        tmp_dir=tmp_dir,
    )
    return all(result.status == WorkflowJobStatus.SUCCEEDED for result in results)


async def deploy_app(
    deployment_job: WorkflowJob,
    app: AppDeployment,
    stack_pack: StackPack,
    tmp_dir: Path,
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
        tmp_dir=tmp_dir,
    )

    return results[0]


async def execute_deployment_workflow(
    run: WorkflowRun,
):
    stack_packs = get_stack_packs()
    project_id = run.project_id
    with TempDir() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        logger.info(f"Deploying project {run.project_id}")
        iac_storage = get_iac_storage()
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

            logger.info(f"Rerunning pack with live state")
            await rerun_pack_with_live_state(
                project,
                common_app,
                common_stack,
                iac_storage,
                binary_storage,
                live_state,
                stack_packs,
                tmp_dir_str,
            )

            logger.info(f"Deploying app stacks")
            email = run.notification_email
            success = await deploy_applications(
                deployment_jobs=deploy_app_jobs,
                tmp_dir=tmp_dir,
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
    iac_storage = get_iac_storage()
    binary_storage = get_binary_storage()
    stack_pack = stackpacks[app.get_app_id()]
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
                f"Updating Common Resources, then deploying {app.get_app_id()}."
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
        with TempDir() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)

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
            await app.run_app(
                stack_pack=stack_pack,
                dir=str(tmp_dir),
                iac_storage=iac_storage,
                binary_storage=binary_storage,
                imports=constraints,
            )

            await deploy_app(
                deployment_job=deploy_app_job,
                app=app,
                stack_pack=stack_pack,
                tmp_dir=tmp_dir,
            )
            complete_workflow_run(run)
            if run.notification_email is not None:
                app_data = [
                    AppData(
                        app_name=app.display_name or app.app_id(),
                        login_url=app.outputs.get("URL"),
                    )
                ]
                send_deployment_success_email(
                    get_ses_client(), run.notification_email, app_data
                )
    except Exception as e:
        abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
        if app.status == AppLifecycleStatus.PENDING.value:
            app.transition_status(
                WorkflowJobStatus.FAILED, WorkflowJobType.DEPLOY, str(e)
            )
