import os

import asyncclick as click
from pydantic_yaml import parse_yaml_file_as

from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import (
    RunEngineRequest,
    RunEngineResult,
    run_engine,
)
from src.stack_pack import StackPack


@click.group()
async def iac():
    pass


@iac.command()
@click.option(
    "--file", prompt="yaml file", help="The yaml file noting the iac scaffold."
)
@click.option("--engine-path", prompt="engine path", help="The engine path")
@click.option("--iac-binary-path", prompt="iac binary path", help="The iac path.")
@click.option("--project-name", prompt="project name", help="The project name.")
@click.option("--output-dir", prompt="output directory", help="The output directory.")
async def generate_iac(
    file: str,
    engine_path: str,
    iac_binary_path: str,
    project_name: str,
    output_dir: str,
):
    try:
        sp = parse_yaml_file_as(StackPack, file)
    except Exception as e:
        raise ValueError(f"Failed to parse {file}") from e

    os.environ.update({"ENGINE_PATH": engine_path})
    os.environ.update({"IAC_PATH": iac_binary_path})
    request = RunEngineRequest(
        constraints=sp.to_constraints({}),
        tmp_dir=output_dir,
    )

    result: RunEngineResult = await run_engine(request)
    await export_iac(
        ExportIacRequest(
            input_graph=result.resources_yaml,
            name=project_name,
            tmp_dir=output_dir,
        )
    )
