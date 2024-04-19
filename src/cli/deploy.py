# Path: src/api/state_machine.py
# Compare this snippet from src/deployer/pulumi/manager.py:


from datetime import datetime, timezone
from pathlib import Path

import asyncclick as click
from pulumi import automation as auto

from src.cli.engine import build_app, generate_iac, read_live_state
from src.cli.util import get_project_and_app
from src.dependencies.injection import get_pulumi_state_bucket_name
from src.deployer.models.workflow_job import WorkflowJob, WorkflowJobStatus
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.project import get_stack_pack
from src.project.actions import run_actions
from src.project.common_stack import CommonStack
from src.project.live_state import LiveState
from src.project.models.app_deployment import AppDeployment
from src.util.logging import logger
from src.util.tmp import TempDir


@click.command("deploy")
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
async def deploy_workflow(run_id: str, job_number: int):
    workflow_job = WorkflowJob.get(run_id, job_number)
    project, app = get_project_and_app(workflow_job)
    logger.info(
        f"Deploying {project.id}/{app.app_id} for deployment job {run_id}/{job_number}"
    )
    try:
        workflow_job.update(
            actions=[WorkflowJob.status.set(WorkflowJobStatus.IN_PROGRESS.value)]
        )
        live_state = await read_live_state(
            workflow_job.project_id(), CommonStack.COMMON_APP_NAME
        )
        with TempDir() as tmp_dir:
            run_engine_result = await build_app(workflow_job, tmp_dir, live_state)
            await generate_iac(run_engine_result, workflow_job, tmp_dir)
            run_pre_deploy_hooks(workflow_job, live_state)
            deploy_status, deploy_message = await deploy(workflow_job, tmp_dir)
            workflow_job.update(
                actions=[
                    WorkflowJob.status.set(deploy_status.value),
                    WorkflowJob.status_reason.set(deploy_message),
                    WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
                ]
            )
            return {"status": deploy_status.value, "message": deploy_message}
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


def run_pre_deploy_hooks(deployment_job: WorkflowJob, live_state: LiveState):
    logger.info(f"Running pre-deploy hooks for {deployment_job.composite_key()}")
    project, app = get_project_and_app(deployment_job)
    run_actions(app, project, live_state)
    return


def get_pulumi_config(deployment_job: WorkflowJob) -> dict[str, str]:
    logger.info(f"Getting pulumi config for {deployment_job.composite_key()}")
    stack_pack = get_stack_pack(deployment_job)
    project, app = get_project_and_app(deployment_job)
    pulumi_config = stack_pack.get_pulumi_configs(app.get_configurations())
    if stack_pack.id != CommonStack.COMMON_APP_NAME:
        common_app = AppDeployment.get(
            project.id,
            AppDeployment.compose_range_key(
                app_id=CommonStack.COMMON_APP_NAME,
                version=project.apps[CommonStack.COMMON_APP_NAME],
            ),
        )
        common_config = CommonStack([stack_pack], []).get_pulumi_configs(
            common_app.get_configurations()
        )
        pulumi_config.update(common_config)
    return pulumi_config


async def deploy(
    deployment_job: WorkflowJob, tmp_dir: Path
) -> tuple[WorkflowJobStatus, str]:
    logger.info(f"Deploying app for deployment job {deployment_job.composite_key()}")
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    project, app = get_project_and_app(deployment_job)
    run_id = deployment_job.partition_key
    logger.info(
        f"Building {project_id}/{app_id}, deployment id {deployment_job.composite_key()}"
    )

    pulumi_config = get_pulumi_config(deployment_job)

    builder = AppBuilder(tmp_dir, get_pulumi_state_bucket_name())
    stack = builder.prepare_stack(deployment_job)
    builder.configure_aws(
        stack,
        project.region,
        project.assumed_role_arn,
        project.assumed_role_external_id,
    )
    for k, v in pulumi_config.items():
        stack.set_config(k, auto.ConfigValue(v, secret=True))
    deployer = AppDeployer(
        stack,
        DeploymentDir(project_id, run_id),
    )
    logger.info(
        f"Deploying {project_id}/{app_id}, deployment id {deployment_job.composite_key()}"
    )
    return await deployer.deploy()
