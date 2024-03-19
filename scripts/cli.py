import asyncclick as click

from scripts.dynamodb import dynamodb
from scripts.iac_generator import iac


@click.group()
async def cli():
    pass


if __name__ == "__main__":
    cli.add_command(dynamodb)
    cli.add_command(iac)
    cli(_anyio_backend="asyncio")
