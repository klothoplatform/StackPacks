import asyncclick as click

from scripts.dynamodb import dynamodb
from scripts.iac_generator import iac
from scripts.policy_generator import policy_gen


@click.group()
async def cli():
    pass


if __name__ == "__main__":
    cli.add_command(dynamodb)
    cli.add_command(iac)
    cli.add_command(policy_gen)
    cli(_anyio_backend="asyncio")
