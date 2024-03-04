import json
import logging
import os
from pathlib import Path
from typing import List, NamedTuple, Dict, Optional
from src.util.tmp import TempDir

import yaml

from src.engine_service.engine_commands.util import (
    run_engine_command,
    EngineException,
)

log = logging.getLogger(__name__)

KEEP_TMP = os.environ.get("KEEP_TMP", False)


class RunEngineRequest(NamedTuple):
    constraints: List[dict]
    tmp_dir: str
    input_graph: str = None


class RunEngineResult(NamedTuple):
    resources_yaml: str
    topology_yaml: str
    iac_topology: str
    config_errors: List[Dict] = []
    policy: str = None


async def run_engine(request: RunEngineRequest) -> RunEngineResult:
    print(request.constraints)

    dir = Path(request.tmp_dir).absolute()
    args = []

    if request.input_graph is not None:
        with open(dir / "graph.yaml", "w") as file:
            file.write(request.input_graph)
        args.append("--input-graph")
        args.append(f"{dir}/graph.yaml")

    if request.constraints is not None:
        with open(dir / "constraints.yaml", "w") as file:
            file.write(yaml.dump({"constraints": request.constraints}))
        args.append("--constraints")
        args.append(f"{dir}/constraints.yaml")

    args.extend(
        [
            "--provider",
            "aws",
            "--output-dir",
            str(dir),
        ]
    )

    error_details = []
    try:
        await run_engine_command(
            "Run",
            *args,
            cwd=dir,
        )
    except EngineException as e:
        if e.returncode == 1:
            raise e
        error_details = json.loads(e.stdout)

    with open(dir / "dataflow-topology.yaml") as file:
        topology_yaml = file.read()

    with open(dir / "iac-topology.yaml") as file:
        iac_topology = file.read()

    with open(dir / "resources.yaml") as file:
        resources_yaml = file.read()

    with open(dir / "deployment_permissions_policy.json") as file:
        policy = file.read()

    return RunEngineResult(
        resources_yaml=resources_yaml,
        topology_yaml=topology_yaml,
        iac_topology=iac_topology,
        # NOTE: This assumes that all non-FailedRun errors are config errors
        # This is true for now, but keep an eye in the future
        config_errors=error_details,
        policy=policy,
    )
