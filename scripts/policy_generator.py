import asyncio
from pathlib import Path

import asyncclick as click

from src.engine_service.engine_commands.run import RunEngineRequest, run_engine
from src.project import StackPack, get_stack_packs
from src.project.common_stack import CommonStack
from src.util.tmp import TempDir


@click.group()
async def policy_gen():
    pass


@policy_gen.command()
async def generate_policies():
    with TempDir() as tmp_dir:
        sps = get_stack_packs()
        common = CommonStack(list(sps.values()), [])
        imports = common.to_constraints({})
        await asyncio.gather(*[gen_policy(sp, tmp_dir, imports) for sp in sps.values()])


async def gen_policy(sp: StackPack, tmp_dir: Path, imports: list):
    app_dir = tmp_dir / sp.id
    app_dir.mkdir(parents=True, exist_ok=True)
    constraints = sp.to_constraints(sp.final_config({}))
    constraints.extend(imports)
    engine_result = await run_engine(
        RunEngineRequest(
            tag="gen_policy",
            constraints=constraints,
            tmp_dir=app_dir,
        )
    )
    policy_path = Path("policies") / f"{sp.id}.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(engine_result.policy)
