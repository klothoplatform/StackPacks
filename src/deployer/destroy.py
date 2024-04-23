import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from aiomultiprocess import Pool

from src.dependencies.injection import get_iac_storage, get_pulumi_state_bucket_name
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
from src.deployer.models.workflow_run import WorkflowRun
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.util import get_app_workflows, get_project_and_app
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from src.util.logging import logger
from src.util.tmp import TempDir


async def destroy_workflow(job_id: str, job_number: int):
    logger.info(f"Received destroy request for {job_id}/{job_number}")
    workflow_job = WorkflowJob.get(job_id, job_number)
    project, app = get_project_and_app(workflow_job)
    logger.info(
        f"Destroying {project.id}/{app.app_id()} for deployment job {job_id}/{job_number}"
    )
    try:
        workflow_job.update(
            actions=[WorkflowJob.status.set(WorkflowJobStatus.IN_PROGRESS.value)]
        )
        with TempDir() as tmp_dir:
            destroy_status, destroy_message = destroy(workflow_job, tmp_dir)
            workflow_job.update(
                actions=[
                    WorkflowJob.status.set(destroy_status.value),
                    WorkflowJob.status_reason.set(destroy_message),
                    WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
                ]
            )
            return {"status": destroy_status.value, "message": destroy_message}
    except Exception as e:
        logger.error(f"Error destroying {job_id}/{job_number}: {e}", exc_info=True)
        workflow_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.FAILED.value),
                WorkflowJob.status_reason.set(str(e)),
            ]
        )
        return {"status": WorkflowJobStatus.FAILED.value, "message": "Internal Error"}


def can_destroy(project_id: str, app_id: str):
    logger.info(f"Checking if {app_id} can be destroyed in project {project_id}")
    project = Project.get(project_id)
    if app_id != CommonStack.COMMON_APP_NAME:
        return True
    for app_name in project.apps.keys():
        if app_name != CommonStack.COMMON_APP_NAME:
            continue
        _, status, _ = AppDeployment.get_status(project_id, app_name)
        if (
            status != AppLifecycleStatus.UNINSTALLED
            and status != AppLifecycleStatus.NEW
        ):
            return False
    return True


def destroy(
    deployment_job: WorkflowJob, tmp_dir: Path
) -> tuple[WorkflowJobStatus, str]:
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    run_id = deployment_job.run_composite_key()
    project, app = get_project_and_app(deployment_job)

    logger.info(
        f"Destroying {app_id} in project {project_id} with job id {deployment_job.composite_key()}"
    )
    iac_storage = get_iac_storage()
    project = Project.get(project_id)
    app = AppDeployment.get_latest_deployed_version(project_id, app_id)

    iac = iac_storage.get_iac(project_id, app_id, app.version())
    builder = AppBuilder(tmp_dir, get_pulumi_state_bucket_name())
    builder.write_iac_to_disk(iac)
    stack = builder.prepare_stack(deployment_job)
    builder.configure_aws(
        stack,
        project.region,
        project.assumed_role_arn,
        project.assumed_role_external_id,
    )
    deployer = AppDeployer(
        stack,
        DeploymentDir(project_id, run_id),
    )
    return deployer.destroy_and_remove_stack()


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
                project_id=run.project_id,
                workflow_type=run.workflow_type(),
                owning_app_id=run.app_id(),
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
            project_id=run.project_id,
            workflow_type=run.workflow_type(),
            owning_app_id=run.app_id(),
            run_number=run.run_number(),
        ),
        job_type=WorkflowJobType.DESTROY,
        modified_app_id=CommonStack.COMMON_APP_NAME,
        initiated_by=run.initiated_by,
        dependencies=[job.composite_key() for job in destroy_app_jobs],
    )
    return destroy_common_job


async def run_full_destroy_workflow(run: WorkflowRun, common_job: WorkflowJob):

    try:
        logger.info(f"Starting destroy workflow for {run.composite_key()}")
        start_workflow_run(run)
        logger.info(f"Getting app workflows for {run.composite_key()}")
        app_flows = get_app_workflows(run)
        logger.info(f"App workflows: {app_flows}")
        results = None
        async with Pool() as pool:
            tasks = []
            for app_flow in app_flows:
                task = pool.apply(
                    destroy_workflow,
                    kwds=dict(
                        job_id=app_flow["id"],
                        job_number=app_flow["job_number"],
                    ),
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            logger.info(f"Tasks: {tasks}")
    except Exception as e:
        logger.error(f"Error destroying {run.composite_key()}: {e}", exc_info=True)
        abort_workflow_run(run)
    try:
        logger.info(results)
        if all(result["status"] == "SUCCEEDED" for result in results):
            logger.info(f"aborting destroy workflow for {run.composite_key()}")
            abort_workflow_run(run)

        if common_job is not None:
            logger.info(f"destroying common stack for {run.composite_key()}")
            async with Pool() as pool:
                tasks = []
                task = pool.apply(
                    destroy_workflow,
                    kwds=dict(
                        job_id=run.composite_key(),
                        job_number=common_job.job_number,
                    ),
                )
                tasks.append(task)
                results = await asyncio.gather(*tasks)
                logger.info(f"Tasks: {tasks}")

        logger.info(f"completing destroy workflow for {run.composite_key()}")
        complete_workflow_run(run)
    except Exception as e:
        logger.error(f"Error destroying {run.composite_key()}: {e}", exc_info=True)
        complete_workflow_run(run)
