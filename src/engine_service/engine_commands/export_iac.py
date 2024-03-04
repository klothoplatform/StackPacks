import tempfile
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

from src.engine_service.engine_commands.util import run_iac_command


class ExportIacRequest(NamedTuple):
    input_graph: str
    name: str
    tmp_dir: str
    provider: str = "pulumi"


async def export_iac(request: ExportIacRequest):
    tmp_dir = request.tmp_dir
    dir = Path(tmp_dir).absolute()

    args = []

    with open(dir / "graph.yaml", "w") as file:
        file.write(request.input_graph)
    args.append("--input-graph")
    args.append(f"{dir}/graph.yaml")

    args.extend(
        [
            "--provider",
            "pulumi",
            "--output-dir",
            str(dir),
            "--app-name",
            request.name,
        ]
    )

    await run_iac_command(
        "Generate",
        *args,
        cwd=dir,
    )
