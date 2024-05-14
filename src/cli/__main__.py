import asyncclick as click

from src.deployer.deploy import deploy_workflow
from src.deployer.destroy import destroy_workflow
from src.deployer.models.util import (
    abort_workflow_run,
    complete_workflow_run,
    start_workflow_run,
)
from src.deployer.models.workflow_job import WorkflowJobStatus
from src.deployer.models.workflow_run import WorkflowRun
from src.deployer.util import get_app_workflows
from src.deployer.util import send_email as send_email_util
from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import RunEngineRequest, run_engine
from src.project import get_stack_packs
from src.project.common_stack import CommonStack
from src.util.logging import logger


@click.group()
async def cli():
    pass


@cli.command("deploy")
@click.option(
    "--job-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
@click.option(
    "--job-number",
    type=int,
    prompt="The job number",
    help="The job number of the workflow run",
)
async def deploy(job_id: str, job_number: int):
    result = await deploy_workflow(job_id, job_number)
    if result.status != WorkflowJobStatus.SUCCEEDED:
        raise Exception(f"Deployment {result.status}: {result.message}")


@cli.command("destroy")
@click.option(
    "--job-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
@click.option(
    "--job-number",
    type=int,
    prompt="The job number",
    help="The job number of the workflow run",
)
async def destroy(job_id: str, job_number: int):
    result = await destroy_workflow(job_id, job_number)
    if result.status != WorkflowJobStatus.SUCCEEDED:
        raise Exception(f"Destroy {result.status}: {result.message}")


@cli.command("get-app-workflows")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
def get_app_workflows_cmd(project_id: str, run_id: str):
    logger.info(f"Getting workflows for {project_id}/{run_id}")
    workflow_run = WorkflowRun.get(project_id, run_id)
    return get_app_workflows(workflow_run)


@cli.command("send-email")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
def send_email(project_id: str, run_id: str):
    logger.info(f"Sending email for {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    send_email_util(run)


@cli.command("abort-workflow")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
def abort_workflow(project_id: str, run_id: str):
    logger.info(f"Aborting workflow {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    abort_workflow_run(run)
    return {"status": "success", "message": "Workflow run aborted"}


@cli.command("start-workflow")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
def start_workflow(project_id: str, run_id: str):
    logger.info(f"Starting workflow {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    start_workflow_run(run)
    return {"status": "success", "message": "Workflow run started"}


@cli.command("complete-workflow")
@click.option(
    "--project-id", prompt="The project id", help="The id of the stacksnap project"
)
@click.option(
    "--run-id",
    prompt="The workflow id",
    help="The range key (composite key) of the workflow run",
)
def complete_workflow(project_id: str, run_id: str):
    logger.info(f"Completing workflow {project_id}/{run_id}")
    run = WorkflowRun.get(project_id, run_id)
    complete_workflow_run(run)
    return {"status": "success", "message": "Workflow run completed"}


@cli.command("build-app")
@click.argument("app")
@click.option(
    "--out-dir", "-o", help="The directory to write the output to", default="."
)
async def build_app(app: str, out_dir: str):
    sps = get_stack_packs()
    if app not in sps:
        raise Exception(f"App {app} not found in stack packs")
    sp = sps[app]
    constraints = sp.to_constraints({}, "us-east-1")
    common = CommonStack([sp], [])
    constraints.extend(common.to_constraints({}, "us-east-1"))
    result = await run_engine(
        RunEngineRequest(tag="cli", constraints=constraints, tmp_dir=out_dir)
    )
    await export_iac(
        ExportIacRequest(
            input_graph=result.resources_yaml,
            name=app,
            tmp_dir=out_dir,
        )
    )


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
