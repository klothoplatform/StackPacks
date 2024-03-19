# import anyio as _
# import asyncclick as click

import asyncclick as click

from scripts.dynamodb import dynamodb
from scripts.iac_generator import iac

# @click.group()
# async def cli():
#     pass

# cli.add_command(dynamodb)
# cli.add_command(iac)

# if __name__ == "__main__":

#     cli()


# You can use all of click's features as per its documentation.
# Async commands are supported seamlessly; they just work.


@click.group()
async def cli():
    pass


# @click.group()
# async def dynamodb():
#     pass

# @dynamodb.command()
# @click.option("--count", default=1, help="Number of greetings.")
# @click.option("--name", prompt="Your name", help="The person to greet.")
# async def hello(count, name):
#     """Simple program that greets NAME for a total of COUNT times."""
#     for x in range(count):
#         if x: await anyio.sleep(0.1)
#         click.echo(f"Hello, {name}!")

if __name__ == "__main__":
    cli.add_command(dynamodb)
    cli.add_command(iac)
    cli(_anyio_backend="asyncio")  # or asyncio

# You can use your own event loop:
#    import anyio
#    async def main():
#        await hello.main()
#    if __name__ == '__main__':
#        anyio.run(main)
# This is useful for testing.
