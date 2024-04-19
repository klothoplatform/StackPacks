import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from aiomultiprocess import Pool
from pulumi import automation as auto

from src.dependencies.injection import get_iac_storage, get_pulumi_state_bucket_name
from src.deployer.deploy import DeploymentResult, StackDeploymentRequest
from src.deployer.models.pulumi_stack import PulumiStack
from src.deployer.models.util import abort_workflow_run, complete_workflow_run
from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowType,
)
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from src.project.storage.iac_storage import IaCDoesNotExistError
from src.util.logging import logger
from src.util.tmp import TempDir


async def run_destroy(
    destroy_job: WorkflowJob,
    region: str,
    assume_role_arn: str,
    iac: bytes,
    app_dir: Path,
    pulumi_config: Optional[dict[str, str]] = None,
    external_id: Optional[str] = None,
) -> DeploymentResult:
    if pulumi_config is None:
        pulumi_config = {}
    project_id = destroy_job.project_id()
    run_id = destroy_job.run_composite_key()
    pulumi_stack = PulumiStack(
        project_name=project_id,
        name=PulumiStack.sanitize_stack_name(destroy_job.modified_app_id),
        status=WorkflowJobStatus.IN_PROGRESS.value,
        status_reason="Destroy in progress",
        created_by=destroy_job.initiated_by,
    )

    try:
        pulumi_stack.save()
        destroy_job.update(
            actions=[
                WorkflowJob.iac_stack_composite_key.set(pulumi_stack.composite_key()),
            ]
        )
        builder = AppBuilder(app_dir, get_pulumi_state_bucket_name())
        builder.write_iac_to_disk(iac)
        stack = builder.prepare_stack(pulumi_stack)
        for k, v in pulumi_config.items():
            stack.set_config(k, auto.ConfigValue(v, secret=True))
        builder.configure_aws(stack, region, assume_role_arn, external_id=external_id)
        deployer = AppDeployer(
            stack,
            DeploymentDir(project_id, run_id),
        )
        result_status, reason = await deployer.destroy_and_remove_stack()
        pulumi_stack.update(
            actions=[
                PulumiStack.status.set(result_status.value),
                PulumiStack.status_reason.set(reason),
            ]
        )
        destroy_job.update(
            actions=[
                WorkflowJob.status.set(result_status.value),
                WorkflowJob.status_reason.set(reason),
                WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
            ]
        )
        return DeploymentResult(
            manager=None, status=result_status, reason=reason, stack=pulumi_stack
        )
    except Exception as e:
        logger.error(
            f"Error destroying {destroy_job.composite_key()}: {e}", exc_info=True
        )
        pulumi_stack.update(
            actions=[
                PulumiStack.status.set(WorkflowJobStatus.FAILED.value),
                PulumiStack.status_reason.set(str(e)),
            ]
        )
        destroy_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.FAILED.value),
                WorkflowJob.status_reason.set(str(e)),
                WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
            ]
        )
        return DeploymentResult(
            manager=None,
            status=WorkflowJobStatus.FAILED,
            reason=str(e),
            stack=pulumi_stack,
        )


async def run_destroy_application(
    destroy_request: StackDeploymentRequest,
    tmp_dir: Path,
) -> DeploymentResult:
    project_id = destroy_request.workflow_job.project_id()
    app_id = destroy_request.workflow_job.modified_app_id

    logger.info(
        f"Destroying {app_id} in project {project_id} with job id {destroy_request.workflow_job.composite_key()}"
    )
    iac_storage = get_iac_storage()
    project = Project.get(project_id)
    app = AppDeployment.get_latest_deployed_version(project_id, app_id)
    if app is None:
        job_status = WorkflowJobStatus.SUCCEEDED
        logger.info(f"Skipping destroy for {app_id} as it is not deployed")
        destroy_request.workflow_job.update(
            actions=[
                WorkflowJob.status.set(job_status.value),
                WorkflowJob.status_reason.set("Not deployed"),
                WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
            ]
        )
        app = AppDeployment.get_latest_version(project_id, app_id)
        if app and app.status not in [
            AppLifecycleStatus.NEW.value,
            AppLifecycleStatus.UNINSTALLED.value,
        ]:
            app.transition_status(
                status=job_status, action=WorkflowJobType.DESTROY, reason="Not deployed"
            )
        return DeploymentResult(
            manager=None,
            status=WorkflowJobStatus.SUCCEEDED,
            reason="Not deployed",
            stack=None,
        )
    destroy_request.workflow_job.update(
        actions=[
            WorkflowJob.status.set(WorkflowJobStatus.IN_PROGRESS.value),
            WorkflowJob.status_reason.set("Destroy in progress"),
            WorkflowJob.initiated_at.set(datetime.now(timezone.utc)),
        ],
    )
    try:
        iac = iac_storage.get_iac(project_id, app_id, app.version())
    except IaCDoesNotExistError:
        # This state could happen if an application's iac failed to generate.
        # Since other applications and the common stack could have been deployed
        # don't fail the destroy process, just log and continue.
        logger.info(f"Skipping destroy for {app.app_id} as iac does not exist")
        destroy_request.workflow_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value),
                WorkflowJob.status_reason.set("IaC does not exist"),
                WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
            ]
        )
        return DeploymentResult(
            manager=None,
            status=WorkflowJobStatus.SUCCEEDED,
            reason="IaC does not exist",
            stack=None,
        )
    app.transition_status(
        WorkflowJobStatus.IN_PROGRESS, WorkflowJobType.DESTROY, "Destroy in progress"
    )
    result = await run_destroy(
        destroy_job=destroy_request.workflow_job,
        region=project.region,
        assume_role_arn=project.assumed_role_arn,
        iac=iac,
        external_id=project.assumed_role_external_id,
        app_dir=tmp_dir / app.app_id(),
    )
    iac_composite_key = (
        result.stack.composite_key()
        if result.status != WorkflowJobStatus.SUCCEEDED
        else None
    )

    app.update(
        actions=[
            AppDeployment.outputs.set({}),
            AppDeployment.iac_stack_composite_key.set(iac_composite_key),
            AppDeployment.deployments.add(
                {destroy_request.workflow_job.composite_key()}
            ),
        ]
    )
    app.transition_status(result.status, WorkflowJobType.DESTROY, result.reason)
    logger.info(f"DESTROY of {app.app_id()} complete. Status: {result.status}")
    return result


async def run_concurrent_destroys(
    destroy_requests: list[StackDeploymentRequest],
    tmp_dir: Path,
) -> Tuple[list[str], list[DeploymentResult]]:
    logger.info(f"Running {len(destroy_requests)} destroys")

    async with Pool() as pool:
        tasks = []
        app_order = []
        for destroy_request in destroy_requests:
            task = pool.apply(
                run_destroy_application,
                kwds=dict(
                    destroy_request=destroy_request,
                    tmp_dir=tmp_dir,
                ),
            )
            app_order.append(destroy_request.workflow_job.modified_app_id)
            tasks.append(task)

        gathered = await asyncio.gather(*tasks)
        logger.info(f"Tasks: {tasks}")
        return app_order, gathered


async def destroy_applications(
    destroy_jobs: list[WorkflowJob],
    tmp_dir: Path,
) -> bool:
    deployment_stacks: list[StackDeploymentRequest] = []
    for job in destroy_jobs:
        if job.modified_app_id == CommonStack.COMMON_APP_NAME:
            continue
        deployment_stacks.append(
            StackDeploymentRequest(
                workflow_job=job,
                pulumi_config={},
            )
        )

    order, results = await run_concurrent_destroys(
        destroy_requests=deployment_stacks,
        tmp_dir=tmp_dir,
    )

    return all(
        result.status in [WorkflowJobStatus.SUCCEEDED, WorkflowJobStatus.SKIPPED]
        for result in results
    )


async def destroy_app(
    destroy_job: WorkflowJob,
    tmp_dir: Path,
) -> DeploymentResult:
    logger.info(f"Destroying app {destroy_job.modified_app_id}")
    _, results = await run_concurrent_destroys(
        [
            StackDeploymentRequest(
                workflow_job=destroy_job,
                pulumi_config={},
            )
        ],
        tmp_dir=tmp_dir,
    )
    return results[0]


async def execute_destroy_single_workflow(run: WorkflowRun, destroy_common: bool):
    try:
        with TempDir() as tmp_dir:
            project = Project.get(run.project_id)
            destroy_app_job = WorkflowJob.create_job(
                partition_key=WorkflowJob.compose_partition_key(
                    project_id=run.project_id,
                    workflow_type=WorkflowType.DESTROY.value,
                    owning_app_id=run.app_id(),
                    run_number=run.run_number(),
                ),
                job_type=WorkflowJobType.DESTROY,
                modified_app_id=run.app_id(),
                initiated_by=run.initiated_by,
            )

            run.update(
                actions=[
                    WorkflowRun.status.set(WorkflowJobStatus.IN_PROGRESS.value),
                    WorkflowRun.status_reason.set("Destroy in progress"),
                    WorkflowRun.initiated_at.set(datetime.now(timezone.utc)),
                ]
            )

            destroy_common_job = None
            if destroy_common:
                destroy_common_job = WorkflowJob.create_job(
                    partition_key=WorkflowJob.compose_partition_key(
                        project_id=run.project_id,
                        workflow_type=WorkflowType.DESTROY.value,
                        owning_app_id=run.app_id(),
                        run_number=run.run_number(),
                    ),
                    job_type=WorkflowJobType.DESTROY,
                    modified_app_id=CommonStack.COMMON_APP_NAME,
                    initiated_by=run.initiated_by,
                    dependencies=[destroy_app_job.composite_key()],
                )

            result = await destroy_app(destroy_app_job, tmp_dir)

            if destroy_common_job:
                if result.status in [
                    WorkflowJobStatus.SUCCEEDED,
                    WorkflowJobStatus.SKIPPED,
                ]:
                    await destroy_app(destroy_common_job, tmp_dir)
                else:
                    abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
                    return
            complete_workflow_run(run)

    except Exception as e:
        logger.error(f"Error destroying {run.composite_key()}: {e}", exc_info=True)
        abort_workflow_run(run, default_run_status=WorkflowRunStatus.FAILED)
    finally:
        project.update(actions=[Project.destroy_in_progress.set(False)])


async def execute_destroy_all_workflow(
    run: WorkflowRun,
):
    project_id = run.project_id

    logger.info(f"Destroying project {project_id}")
    project = Project.get(project_id)

    try:
        project.update(actions=[Project.destroy_in_progress.set(True)])

        logger.info(f"Destroying app stacks")

        with TempDir() as tmp_dir:
            common_version = project.apps.get(CommonStack.COMMON_APP_NAME, 0)
            if common_version == 0:
                raise ValueError("Common stack not found")

            destroy_app_jobs = [
                WorkflowJob.create_job(
                    partition_key=WorkflowJob.compose_partition_key(
                        project_id=project_id,
                        workflow_type=WorkflowType.DESTROY.value,
                        owning_app_id=None,
                        run_number=run.run_number(),
                    ),
                    job_type=WorkflowJobType.DESTROY,
                    modified_app_id=app_id,
                    initiated_by=run.initiated_by,
                )
                for app_id in project.apps.keys()
                if app_id != CommonStack.COMMON_APP_NAME
            ]

            destroy_common_job = WorkflowJob.create_job(
                partition_key=WorkflowJob.compose_partition_key(
                    project_id=project_id,
                    workflow_type=WorkflowType.DESTROY.value,
                    owning_app_id=None,
                    run_number=run.run_number(),
                ),
                job_type=WorkflowJobType.DESTROY,
                modified_app_id=CommonStack.COMMON_APP_NAME,
                initiated_by=run.initiated_by,
                dependencies=[job.composite_key() for job in destroy_app_jobs],
            )

            run.update(
                actions=[
                    WorkflowRun.status.set(WorkflowJobStatus.IN_PROGRESS.value),
                    WorkflowRun.status_reason.set("Destroy in progress"),
                    WorkflowRun.initiated_at.set(datetime.now(timezone.utc)),
                ]
            )
            for job in [*destroy_app_jobs, destroy_common_job]:
                job.update(
                    actions=[WorkflowJob.status.set(WorkflowJobStatus.PENDING.value)]
                )

            common_app = AppDeployment.get(
                project_id,
                AppDeployment.compose_range_key(
                    CommonStack.COMMON_APP_NAME, common_version
                ),
            )
            common_app.update(
                actions=[
                    AppDeployment.status.set(AppLifecycleStatus.PENDING.value),
                    AppDeployment.status_reason.set(
                        "waiting for applications to be destroyed"
                    ),
                ]
            )

            success = await destroy_applications(
                destroy_jobs=destroy_app_jobs, tmp_dir=tmp_dir
            )
            if not success:
                common_app.transition_status(
                    WorkflowJobStatus.FAILED,
                    WorkflowJobType.DESTROY,
                    "One or more applications failed to destroy",
                )
                abort_workflow_run(run)
                return

            await destroy_app(destroy_job=destroy_common_job, tmp_dir=tmp_dir)
            complete_workflow_run(run)
    except Exception as e:
        logger.error(f"Error destroying project {project_id}: {e}")
        abort_workflow_run(run)
    finally:
        project.update(actions=[Project.destroy_in_progress.set(False)])


def create_destroy_workflow_jobs(
    run: WorkflowRun,
    apps: List[str],
    keep_common: bool = False,
) -> WorkflowJob:
    project_id = run.project_id
    project = Project.get(project_id)

    destroy_app_jobs = [
        WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                project_id=project_id,
                workflow_type=WorkflowType.DESTROY.value,
                owning_app_id=None,
                run_number=run.run_number(),
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id=app_id,
            initiated_by=run.initiated_by,
        )
        for app_id in apps
        if app_id != CommonStack.COMMON_APP_NAME
    ]
    destroy_common = False
    if not keep_common:
        installed_apps = set()
        for a in project.apps:
            if a not in [CommonStack.COMMON_APP_NAME, *apps]:
                app = AppDeployment.get_latest_deployed_version(project.id, a)
                if app is not None:
                    installed_apps.add(a)
        logger.info(f"Installed apps: {installed_apps}")
        if len(installed_apps) == 0:
            project.update(actions=[Project.destroy_in_progress.set(True)])
            destroy_common = True

    if not destroy_common:
        return None
    destroy_common_job = WorkflowJob.create_job(
        partition_key=WorkflowJob.compose_partition_key(
            project_id=project_id,
            workflow_type=WorkflowType.DESTROY.value,
            owning_app_id=None,
            run_number=run.run_number(),
        ),
        job_type=WorkflowJobType.DESTROY,
        modified_app_id=CommonStack.COMMON_APP_NAME,
        initiated_by=run.initiated_by,
        dependencies=[job.composite_key() for job in destroy_app_jobs],
    )
    return destroy_common_job


async def run_full_destroy_workflow(run: WorkflowRun, common_job: WorkflowJob):
    logger.info("GGEWWGEGWEG")
    import anyio

    from src.cli.destroy import destroy_workflow
    from src.cli.workflow_management import (
        abort_workflow,
        complete_workflow,
        get_app_workflows,
        start_workflow,
    )

    try:
        logger.info(f"Starting destroy workflow for {run.composite_key()}")
        start_workflow(run.project_id, run.range_key)
        logger.info(f"Getting app workflows for {run.composite_key()}")
        app_flows = await get_app_workflows(run.project_id, run.range_key)
        logger.info(f"App workflows: {app_flows}")
        results = None
        async with Pool() as pool:
            tasks = []
            for app_flow in app_flows:
                task = pool.apply(
                    destroy_workflow,
                    kwds=dict(
                        run_id=run.range_key,
                        job_number=app_flow["range_key"],
                    ),
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            logger.info(f"Tasks: {tasks}")
        logger.info(results)
        if all(result["status"] == "SUCCEEDED" for result in results):
            logger.info(f"aborting destroy workflow for {run.composite_key()}")
            abort_workflow(run.project_id, run.range_key)

        if common_job is not None:
            logger.info(f"destroying common stack for {run.composite_key()}")
            await destroy_workflow(run.range_key, common_job.job_number)

        logger.info(f"completing destroy workflow for {run.composite_key()}")
        complete_workflow(run.project_id, run.range_key)
    except Exception as e:
        logger.error(f"Error destroying {run.composite_key()}: {e}", exc_info=True)
