# Path: src/api/state_machine.py
# Compare this snippet from src/deployer/pulumi/manager.py:


from datetime import datetime, timezone
from pathlib import Path

import asyncclick as click

from src.cli.util import get_project_and_app
from src.dependencies.injection import get_iac_storage, get_pulumi_state_bucket_name
from src.deployer.models.workflow_job import WorkflowJob, WorkflowJobStatus
from src.deployer.models.workflow_run import WorkflowRun
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from src.util.logging import logger
from src.util.tmp import TempDir


@click.command("destroy")
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
@click.option(
    "--job-number",
    type=int,
    prompt="The job number",
    help="The job number of the workflow run",
)
async def destroy_workflow(run_id: str, job_number: int):
    workflow_job = WorkflowJob.get(run_id, job_number)
    project, app = get_project_and_app(workflow_job)
    logger.info(
        f"Destroying {project.id}/{app.app_id} for deployment job {run_id}/{job_number}"
    )
    try:
        workflow_job.update(
            actions=[WorkflowJob.status.set(WorkflowJobStatus.IN_PROGRESS.value)]
        )
        with TempDir() as tmp_dir:
            destroy_status, destroy_message = await destroy(workflow_job, tmp_dir)
            workflow_job.update(
                actions=[
                    WorkflowJob.status.set(destroy_status.value),
                    WorkflowJob.status_reason.set(destroy_message),
                    WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
                ]
            )
            return {"status": destroy_status.value, "message": destroy_message}
    except Exception as e:
        workflow_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.FAILED.value),
                WorkflowJob.status_reason.set(str(e)),
            ]
        )
        return {"status": WorkflowJobStatus.FAILED.value, "message": "Internal Error"}
    finally:
        app.update(
            actions=[
                AppDeployment.deployments.append(workflow_job.composite_key()),
            ]
        )


@click.command("can_destroy")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--app-id", prompt="The app id", help="The id of the app", default="common"
)
async def can_destroy(project_id: str, app_id: str):
    logger.info(f"Checking if {app_id} can be destroyed in project {project_id}")
    project = Project.get(project_id)
    WorkflowRun.get_latest_run(project_id)
    if app_id != CommonStack.COMMON_APP_NAME:
        return True
    for app_name in project.apps.keys():
        if app_name != CommonStack.COMMON_APP_NAME:
            continue
        _, status = AppDeployment.get_status(project_id, app_name)
        if status != AppLifecycleStatus.UNINSTALLED or status != AppLifecycleStatus.NEW:
            return False
    return True


async def destroy(
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
    return await deployer.destroy_and_remove_stack()
