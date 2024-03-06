import tempfile
from io import BytesIO
from pathlib import Path
from typing import List, NamedTuple
import yaml
import jsons

from src.engine_service.engine_commands.util import run_iac_command


class GetLiveStateRequest(NamedTuple):
    state: dict
    tmp_dir: str
    input_graph: str = None


async def get_live_state(request: GetLiveStateRequest):
    tmp_dir = request.tmp_dir
    dir = Path(tmp_dir)

    args = []

    if request.input_graph is not None:
        with open(dir / "graph.yaml", "w") as file:
            file.write(request.input_graph)
            args.append("--input-graph")
            args.append(f"{tmp_dir}/graph.yaml")

    with open(dir / "state.json", "w") as file:
        file.write(jsons.dumps(request.state))
        args.append("--state-file")
        args.append(f"{dir.absolute()}/state.json")

    args.extend(
        [
            "--provider",
            "pulumi",
        ]
    )

    stdout, stderr = await run_iac_command(
        "GetLiveState",
        *args,
        cwd=dir,
    )
    # returns a resources yaml in stdout
    return stdout
