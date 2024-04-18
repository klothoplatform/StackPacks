import asyncclick as click

from src.dependencies.injection import get_ses_client
from src.deployer.models.util import (
    abort_workflow_run,
    complete_workflow_run,
    start_workflow_run,
)
from src.deployer.models.workflow_run import WorkflowRun
from src.project.models.project import Project
from src.util.aws.ses import AppData, send_deployment_success_email


@click.command("deploy")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
async def get_app_workflows(project_id: str, run_id: str):
    workflow_run = WorkflowRun.get(project_id, run_id)
    jobs = workflow_run.get_jobs()
    return [
        {"hash_key": job.partition_key, "range_key": job.job_number}
        for job in jobs
        if job.modified_app_id != Project.COMMON_APP_NAME
    ]


@click.command("send-email")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
async def send_email(project_id: str, run_id: str):
    run = WorkflowRun.get(project_id, run_id)
    if run.notification_email is not None:
        app_data = []
        for job in run.get_jobs():
            if job.modified_app_id == Project.COMMON_APP_NAME:
                continue
            _, app = job.get_project_and_app()
            app_data.append(
                AppData(
                    app_name=app.display_name or app.app_id(),
                    login_url=app.outputs.get("URL", None) if app.outputs else None,
                )
            )
        send_deployment_success_email(
            get_ses_client(), run.notification_email, app_data
        )


@click.command("abort_workflow")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
async def abort_workflow(project_id: str, run_id: str):
    run = WorkflowRun.get(project_id, run_id)
    abort_workflow_run(run)
    return {"status": "success", "message": "Workflow run aborted"}


@click.command("start_workflow")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
async def start_workflow(project_id: str, run_id: str):
    run = WorkflowRun.get(project_id, run_id)
    start_workflow_run(run)
    return {"status": "success", "message": "Workflow run started"}


@click.command("complete_workflow")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
async def complete_workflow(project_id: str, run_id: str):
    run = WorkflowRun.get(project_id, run_id)
    complete_workflow_run(run)
    return {"status": "success", "message": "Workflow run completed"}
