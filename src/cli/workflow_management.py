import asyncclick as click

from src.cli.util import cli_command
from src.dependencies.injection import get_ses_client
from src.deployer.models.util import (
    abort_workflow_run,
    complete_workflow_run,
    start_workflow_run,
)
from src.deployer.models.workflow_run import WorkflowRun
from src.project.common_stack import CommonStack
from src.util.aws.ses import AppData, send_deployment_success_email
from src.util.logging import logger


# @cli_command
# @click.option(
#     "--project-id", prompt="The project id", help="The id of the stacksnap project"
# )
# @click.option(
#     "--run-id",
#     prompt="The workflow id",
#     help="The range key (composite key) of the workflow run",
# )
def get_app_workflows(project_id: str, run_id: str):
    logger.info(f"Getting workflows for {project_id}/{run_id}")
    workflow_run = WorkflowRun.get(project_id, run_id)
    jobs = workflow_run.get_jobs()
    return [
        {"hash_key": job.partition_key, "range_key": job.job_number}
        for job in jobs
        if job.modified_app_id != CommonStack.COMMON_APP_NAME
    ]


# @cli_command
# @click.option(
#     "--project-id", prompt="The project id", help="The id of the stacksnap project"
# )
# @click.option(
#     "--run-id",
#     prompt="The workflow id",
#     help="The range key (composite key) of the workflow run",
# )
def send_email(project_id: str, run_id: str):
    logger.info(f"Sending email for {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    if run.notification_email is not None:
        app_data = []
        for job in run.get_jobs():
            if job.modified_app_id == CommonStack.COMMON_APP_NAME:
                continue
            _, app = job.get_project_and_app()
            app_data.append(
                AppData(
                    app_name=app.display_name or app.app_id(),
                    login_url=app.outputs.get("URL", None) if app.outputs else None,
                )
            )
        logger.info(f"Sending email to {run.notification_email}")
        send_deployment_success_email(
            get_ses_client(), run.notification_email, app_data
        )


# @cli_command
# @click.option(
#     "--project-id", prompt="The project id", help="The id of the stacksnap project"
# )
# @click.option(
#     "--run-id",
#     prompt="The workflow id",
#     help="The range key (composite key) of the workflow run",
# )
def abort_workflow(project_id: str, run_id: str):
    logger.info(f"Aborting workflow {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    abort_workflow_run(run)
    return {"status": "success", "message": "Workflow run aborted"}


# @cli_command
# @click.option(
#     "--project-id", prompt="The project id", help="The id of the stacksnap project"
# )
# @click.option(
#     "--run-id",
#     prompt="The workflow id",
#     help="The range key (composite key) of the workflow run",
# )
def start_workflow(project_id: str, run_id: str):
    logger.info(f"Starting workflow {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    start_workflow_run(run)
    return {"status": "success", "message": "Workflow run started"}


# @cli_command
# @click.option(
#     "--project-id", prompt="The project id", help="The id of the stacksnap project"
# )
# @click.option(
#     "--run-id",
#     prompt="The workflow id",
#     help="The range key (composite key) of the workflow run",
# )
def complete_workflow(project_id: str, run_id: str):
    logger.info(f"Completing workflow {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    complete_workflow_run(run)
    return {"status": "success", "message": "Workflow run completed"}
