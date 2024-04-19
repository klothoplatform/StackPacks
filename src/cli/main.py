import asyncclick as click

from src.cli.deploy import deploy_workflow
from src.cli.destroy import destroy_workflow
from src.cli.workflow_management import (
    abort_workflow,
    complete_workflow,
    get_app_workflows,
    send_email,
    start_workflow,
)


@click.group()
async def cli():
    pass


if __name__ == "__main__":
    cli.add_command(deploy_workflow)
    cli.add_command(destroy_workflow)
    cli.add_command(abort_workflow)
    cli.add_command(get_app_workflows)
    cli.add_command(send_email)
    cli.add_command(start_workflow)
    cli.add_command(complete_workflow)
    cli.main()
