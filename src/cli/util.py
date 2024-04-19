import functools

import asyncclick as click

from src.deployer.models.workflow_job import WorkflowJob
from src.project import StackPack, get_stack_packs
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project


def cli_command(func):
    @click.command()  # Decorate the function with Click command
    @functools.wraps(func)  # Preserve metadata of the original function
    def wrapper(*args, **kwargs):
        print("Decorator is called")
        return func(*args, **kwargs)

    # Store the original function in a separate attribute
    wrapper._original_func = func
    return wrapper


def get_project_and_app(job: WorkflowJob) -> tuple[Project, AppDeployment]:
    project = Project.get(job.project_id())
    app = AppDeployment.get(
        job.project_id(),
        AppDeployment.compose_range_key(
            app_id=job.modified_app_id, version=project.apps[job.modified_app_id]
        ),
    )
    return project, app


def get_stack_pack(job: WorkflowJob) -> StackPack:
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
