import asyncio
import json
from pathlib import Path

import asyncclick as click

from src.engine_service.engine_commands.run import RunEngineRequest, run_engine
from src.project import StackPack, get_stack_packs
from src.project.common_stack import CommonStack
from src.util.aws.iam import Policy
from src.util.tmp import TempDir


@click.command()
async def policy_gen():
    with TempDir() as tmp_dir:
        sps = get_stack_packs()
        common = CommonStack(list(sps.values()), [])
        imports = common.to_constraints({}, "us-east-1")
        await asyncio.gather(
            gen_policy(common, tmp_dir, []),
            *[gen_policy(sp, tmp_dir, imports) for sp in sps.values()],
        )


async def gen_policy(sp: StackPack, tmp_dir: Path, imports: list):
    app_dir = tmp_dir / sp.id
    app_dir.mkdir(parents=True, exist_ok=True)
    constraints = sp.to_constraints(sp.final_config({}), "us-east-1")
    constraints.extend(imports)
    engine_result = await run_engine(
        RunEngineRequest(
            tag="gen_policy",
            constraints=constraints,
            tmp_dir=app_dir,
        )
    )
    policy = Policy(engine_result.policy)
    if hasattr(sp, "additional_policies"):
        for additional_policy in sp.additional_policies:
            policy.combine(Policy(json.dumps(additional_policy)))
    policy_path = Path("policies") / f"{sp.id}.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(str(policy))
