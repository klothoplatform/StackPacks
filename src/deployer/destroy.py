import asyncio
from dataclasses import dataclass
from typing import Tuple
import uuid
from aiomultiprocess import Pool
from src.dependencies.injection import get_iac_storage
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.models.deployment import (
    DeploymentStatus,
    Deployment,
    DeploymentAction,
    PulumiStack,
)
from pulumi import automation as auto
from src.util.logging import logger
from src.util.tmp import TempDir
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.models.user_app import UserApp
from src.deployer.main import DeploymentResult, StackDeploymentRequest, PROJECT_NAME

async def run_destroy(
    region: str,
    assume_role_arn: str,
    app: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    tmp_dir: TempDir,
) -> DeploymentResult:
    deployment_id = str(uuid.uuid4())
    pulumi_stack = PulumiStack(
        project_name=PROJECT_NAME,
        name=PulumiStack.sanitize_stack_name(app),
        status=DeploymentStatus.IN_PROGRESS.value,
        status_reason="Destroy in progress",
        created_by=user,
    )
    deployment = Deployment(
        id=deployment_id,
        iac_stack_composite_key=pulumi_stack.composite_key(),
        action=DeploymentAction.DESTROY.value,
        status=DeploymentStatus.IN_PROGRESS.value,
        status_reason="Destroy in progress",
        initiated_by=user,
    )

    pulumi_stack.save()
    deployment.save()
    builder = AppBuilder(tmp_dir.dir)
    stack = builder.prepare_stack(iac, pulumi_stack)
    for k, v in pulumi_config.items():
        stack.set_config(k, auto.ConfigValue(v, secret=True))
    builder.configure_aws(stack, assume_role_arn, region)
    deployer = AppDeployer(
        stack,
    )
    result_status, reason = await deployer.destroy_and_remove_stack()
    pulumi_stack.update(
        actions=[
            PulumiStack.status.set(result_status.value),
            PulumiStack.status_reason.set(reason),
        ]
    )
    deployment.update(
        actions=[
            Deployment.status.set(result_status.value),
            Deployment.status_reason.set(reason),
        ]
    )
    return DeploymentResult(
        manager=None, status=result_status, reason=reason, stack=pulumi_stack
    )

async def run_concurrent_destroys(
    region: str,
    assume_role_arn: str,
    stacks: list[StackDeploymentRequest],
    user: str,
) -> Tuple[list[str], list[DeploymentResult]]:

    logger.info(f"Running {len(stacks)} destroys")

    async with Pool() as pool:
        tasks = []
        app_order = []
        for stack in stacks:
            task = pool.apply(
                run_destroy,
                args=(
                    region,
                    assume_role_arn,
                    stack.stack_name,
                    user,
                    stack.iac,
                    stack.pulumi_config,
                    TempDir(),
                ),
            )
            app_order.append(stack.stack_name)
            tasks.append(task)

        gathered = await asyncio.gather(*tasks)
        logger.info(f"Tasks: {tasks}")
        return app_order, gathered



async def tear_down_pack(
    pack_id: str,
):
    logger.info(f"Tearing down pack {pack_id}")
    iac_storage = get_iac_storage()
    user_pack = UserPack.get(pack_id)

    logger.info(f"Destroying app stacks")
    deployment_stacks: list[StackDeploymentRequest] = []
    apps: dict[str, UserApp] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get(UserApp.composite_key(user_pack.id, name), version)
        apps[app.get_app_name()] = app
        iac = iac_storage.get_iac(user_pack.id, app.get_app_name(), version)
        deployment_stacks.append(
            StackDeploymentRequest(stack_name=app.app_id, iac=iac, pulumi_config={})
        )

    order, results = await run_concurrent_destroys(
        user_pack.region, user_pack.assumed_role_arn, deployment_stacks, user_pack.id
    )
    for i, name in enumerate(order):
        app = apps[name]
        result = results[i]
        app.update(
            actions=[
                UserApp.status.set(result.status.value),
                UserApp.status_reason.set(result.reason),
                UserApp.iac_stack_composite_key.set(None),
            ]
        )

    common_version = user_pack.apps.get(UserPack.COMMON_APP_NAME, 0)
    if common_version == 0:
        raise ValueError("Common stack not found")

    logger.info(f"Destroying common stack {common_version}")
    common_pack = UserApp.get(
        UserApp.composite_key(user_pack.id, UserPack.COMMON_APP_NAME), common_version
    )
    iac = iac_storage.get_iac(user_pack.id, common_pack.get_app_name(), common_version)

    order, results = await run_concurrent_destroys(
        user_pack.region,
        user_pack.assumed_role_arn,
        [
            StackDeploymentRequest(
                stack_name=common_pack.app_id, iac=iac, pulumi_config={}
            )
        ],
        user_pack.id,
    )
    common_pack.update(
        actions=[
            UserApp.status.set(results[0].status.value),
            UserApp.status_reason.set(results[0].reason),
            UserApp.iac_stack_composite_key.set(None),
        ]
    )

    return
