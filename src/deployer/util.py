from pydantic import BaseModel

from src.dependencies.injection import get_ses_client
from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.models.workflow_run import WorkflowRun
from src.project import StackPack, get_stack_packs
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from src.util.aws.ses import AppData, send_deployment_success_email
from src.util.logging import logger


def get_project_and_app(job: WorkflowJob) -> tuple[Project, AppDeployment]:
    project = Project.get(job.project_id())
    app = AppDeployment.get(
        job.project_id(),
        AppDeployment.compose_range_key(
            app_id=job.modified_app_id, version=project.apps[job.modified_app_id]
        ),
    )
    return project, app


def get_stack_pack_by_job(job: WorkflowJob) -> StackPack:
    project = Project.get(job.project_id())
    app_id = job.modified_app_id
    stack_packs = get_stack_packs()
    if app_id in stack_packs:
        stack_pack = stack_packs[app_id]
    else:
        stack_pack = CommonStack(
            stack_packs=[stack_packs[a] for a in project.apps if a in stack_packs],
            features=project.features,
        )
    return stack_pack


class JobKeys(BaseModel):
    id: str
    job_number: int


def get_app_workflows(workflow_run: WorkflowRun) -> list[JobKeys]:
    jobs = workflow_run.get_jobs()
    return [
        JobKeys(id=job.partition_key, job_number=job.job_number).model_dump()
        for job in jobs
        if job.modified_app_id != CommonStack.COMMON_APP_NAME
    ]


def send_email(run: WorkflowRun):
    logger.info(f"Sending email for {run.composite_key()}")
    if run.notification_email is not None:
        app_data = []
        for job in run.get_jobs():
            if job.modified_app_id == CommonStack.COMMON_APP_NAME:
                continue
            _, app = get_project_and_app(job)
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
