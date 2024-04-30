import json
import os
from pathlib import Path

import asyncclick as click
from pydantic_yaml import parse_yaml_file_as

from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import (
    RunEngineRequest,
    RunEngineResult,
    run_engine,
)
from src.project import ConfigValues, StackPack


@click.group()
async def iac():
    pass


@iac.command()
@click.option(
    "--file", prompt="yaml file", help="The yaml file noting the iac scaffold."
)
@click.option("--config", help="The config file.")
@click.option("--project-name", prompt="project name", help="The project name.")
@click.option("--output-dir", prompt="output directory", help="The output directory.")
@click.option(
    "--region", prompt="region", help="The region the iac will be deployed to."
)
async def generate_iac(
    file: str, config: str, project_name: str, output_dir: str, region: str
):
    try:
        sp = parse_yaml_file_as(StackPack, file)
    except Exception as e:
        raise ValueError(f"Failed to parse {file}") from e

    user_config = {}
    if config:
        config_path = Path(config)
        if config_path.suffix == ".yaml":
            user_config = parse_yaml_file_as(ConfigValues, config)
        elif config_path.suffix == ".json":
            with open(config_path, "r") as config_path:
                config_dict = json.load(config_path)
                user_config = ConfigValues(config_dict.items())
        else:
            raise ValueError(f"Invalid config file (must be json or yaml): {config}")

    os.makedirs(output_dir, exist_ok=True)

    request = RunEngineRequest(
        tag=project_name,
        constraints=sp.to_constraints(user_config, region),
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
    sp.copy_files(user_config, Path(output_dir), root=Path(file).parent)
