import asyncio
from typing import Tuple
import uuid
from aiomultiprocess import Pool
from src.deployer.main import DeploymentResult, PROJECT_NAME, StackDeploymentRequest
from src.dependencies.injection import get_iac_storage
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.pulumi.manager import LiveState, AppManager
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
from src.stack_pack import ConfigValues, StackPack
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.storage.iac_storage import IacStorage


async def build_and_deploy(
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
        status_reason="Deployment in progress",
        created_by=user,
    )
    deployment = Deployment(
        id=deployment_id,
        iac_stack_composite_key=pulumi_stack.composite_key(),
        action=DeploymentAction.DEPLOY.value,
        status=DeploymentStatus.IN_PROGRESS.value,
        status_reason="Deployment in progress",
        initiated_by=user,
    )

    pulumi_stack.save()
    deployment.save()
    builder = AppBuilder(tmp_dir.dir)
    stack = builder.prepare_stack(iac, pulumi_stack)
    builder.configure_aws(stack, assume_role_arn, region)
    for k, v in pulumi_config.items():
        stack.set_config(k, auto.ConfigValue(v, secret=True))
    deployer = AppDeployer(
        stack,
    )
    result_status, reason = await deployer.deploy()
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
        manager=AppManager(stack),
        status=result_status,
        reason=reason,
        stack=pulumi_stack,
    )


async def run_concurrent_deployments(
    region: str,
    assume_role_arn: str,
    stacks: list[StackDeploymentRequest],
    user: str,
) -> Tuple[list[str], list[DeploymentResult]]:
    # This version of the function creates an empty list tasks, then iterates over the stacks list.
    # For each stack, it applies the build_and_deploy function using the pool, awaits the result, and appends it to the tasks list.
    # This way, each task is awaited individually in an async context.

    logger.info(f"Running {len(stacks)} deployments")

    async with Pool() as pool:
        tasks = []
        app_order = []
        for stack in stacks:
            task = pool.apply(
                build_and_deploy,
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


async def deploy_common_stack(
    user_pack: UserPack,
    common_pack: UserApp,
    common_stack: CommonStack,
    iac_storage: IacStorage,
):
    common_version = common_pack.version
    logger.info(f"Deploying common stack {common_version}")
    iac = iac_storage.get_iac(user_pack.id, common_pack.get_app_name(), common_version)

    pulumi_config = common_stack.get_pulumi_configs(common_pack.configuration.items())
    order, results = await run_concurrent_deployments(
        user_pack.region,
        user_pack.assumed_role_arn,
        [
            StackDeploymentRequest(
                stack_name=common_pack.app_id, iac=iac, pulumi_config=pulumi_config
            )
        ],
        user_pack.id,
    )
    common_pack.update(
        actions=[
            UserApp.status.set(results[0].status.value),
            UserApp.status_reason.set(results[0].reason),
            UserApp.iac_stack_composite_key.set(results[0].stack.composite_key()),
        ]
    )
    return results[0].manager


async def rerun_pack_with_live_state(
    user_pack: UserPack,
    common_pack: UserApp,
    common_stack: CommonStack,
    iac_storage: IacStorage,
    live_state: LiveState,
    sps: dict[str, StackPack],
):
    logger.info(f"Rerunning pack {user_pack.id} with imports")

    configuration: dict[str, ConfigValues] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get(UserApp.composite_key(user_pack.id, name), version)
        configuration[name] = app.get_configurations()

    await user_pack.run_pack(
        sps,
        configuration,
        iac_storage,
        increment_versions=False,
        imports=live_state.to_constraints(common_stack, common_pack.configuration),
    )
    return


async def deploy_applications(
    user_pack: UserPack,
    iac_storage: IacStorage,
    sps: dict[str, StackPack],
):
    deployment_stacks: list[StackDeploymentRequest] = []
    apps: dict[str, UserApp] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get(UserApp.composite_key(user_pack.id, name), version)
        apps[app.get_app_name()] = app
        iac = iac_storage.get_iac(user_pack.id, app.get_app_name(), version)
        sp = sps[app.get_app_name()]
        pulumi_config = sp.get_pulumi_configs(app.get_configurations())
        deployment_stacks.append(
            StackDeploymentRequest(
                stack_name=app.app_id, iac=iac, pulumi_config=pulumi_config
            )
        )

    order, results = await run_concurrent_deployments(
        user_pack.region, user_pack.assumed_role_arn, deployment_stacks, user_pack.id
    )
    for i, name in enumerate(order):
        app = apps[name]
        result = results[i]
        app.update(
            actions=[
                UserApp.status.set(result.status.value),
                UserApp.status_reason.set(result.reason),
                UserApp.iac_stack_composite_key.set(result.stack.composite_key()),
            ]
        )


async def deploy_pack(
    pack_id: str,
    sps: dict[str, StackPack],
):
    logger.info(f"Deploying pack {pack_id}")
    iac_storage = get_iac_storage()
    user_pack = UserPack.get(pack_id)

    common_version = user_pack.apps.get(UserPack.COMMON_APP_NAME, 0)
    if common_version == 0:
        raise ValueError("Common stack not found")

    common_pack = UserApp.get(
        UserApp.composite_key(user_pack.id, UserPack.COMMON_APP_NAME), common_version
    )
    common_stack = CommonStack([sp for sp in sps.values()])
    logger.info(f"Deploying common stack")
    manager = await deploy_common_stack(pack_id, sps, common_pack, common_stack)
    live_state = await manager.read_deployed_state()

    logger.info(f"Rerunning pack with live state")
    await rerun_pack_with_live_state(
        user_pack, common_pack, common_stack, iac_storage, live_state, sps
    )

    logger.info(f"Deploying app stacks")
    await deploy_applications(user_pack, iac_storage, sps)
    return
