import asyncio
from pathlib import Path
from typing import Tuple

from aiomultiprocess import Pool
from pulumi import automation as auto

from src.dependencies.injection import get_iac_storage
from src.deployer.deploy import PROJECT_NAME, DeploymentResult, StackDeploymentRequest
from src.deployer.models.deployment import (
    Deployment,
    DeploymentAction,
    DeploymentStatus,
    PulumiStack,
)
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.storage.iac_storage import IaCDoesNotExistError, IacStorage
from src.util.logging import logger
from src.util.tmp import TempDir


async def run_destroy(
    region: str,
    assume_role_arn: str,
    app: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    deployment_id: str,
    tmp_dir: Path,
) -> DeploymentResult:
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
    builder = AppBuilder(tmp_dir)
    stack = builder.prepare_stack(iac, pulumi_stack)
    for k, v in pulumi_config.items():
        stack.set_config(k, auto.ConfigValue(v, secret=True))
    builder.configure_aws(stack, assume_role_arn, region)
    deployer = AppDeployer(
        stack,
        DeploymentDir(user, deployment_id),
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
    tmp_dir: Path,
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
                    stack.deployment_id,
                    tmp_dir / stack.stack_name,
                ),
            )
            app_order.append(stack.stack_name)
            tasks.append(task)

        gathered = await asyncio.gather(*tasks)
        logger.info(f"Tasks: {tasks}")
        return app_order, gathered


async def destroy_common_stack(
    user_pack: UserPack,
    common_pack: UserApp,
    iac_storage: IacStorage,
    deployment_id: str,
    tmp_dir: Path,
):
    common_version = common_pack.version
    logger.info(f"Destroying common stack {common_version}")
    iac = iac_storage.get_iac(user_pack.id, common_pack.get_app_name(), common_version)

    order, results = await run_concurrent_destroys(
        user_pack.region,
        user_pack.assumed_role_arn,
        [
            StackDeploymentRequest(
                stack_name=common_pack.app_id,
                iac=iac,
                pulumi_config={},
                deployment_id=deployment_id,
            )
        ],
        user_pack.id,
        tmp_dir,
    )
    common_pack.update(
        actions=[
            UserApp.status.set(results[0].status.value),
            UserApp.status_reason.set(results[0].reason),
            UserApp.iac_stack_composite_key.set(None),
        ]
    )


async def destroy_applications(
    user_pack: UserPack,
    iac_storage: IacStorage,
    deployment_id: str,
    tmp_dir: Path,
):
    deployment_stacks: list[StackDeploymentRequest] = []
    apps: dict[str, UserApp] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get_latest_version_with_status(
            UserApp.composite_key(user_pack.id, name)
        )
        if app == None:
            # this would mean that nothing has been deployed
            continue
        apps[app.app_id] = app
        try:
            iac = iac_storage.get_iac(user_pack.id, app.get_app_name(), version)
        except IaCDoesNotExistError:
            # This state could happen if an application's iac failed to generate.
            # Since other applications and the common stack could have been deployed
            # don't fail the destroy process, just log and continue.
            logger.info(f"Skipping destroy for {app.app_id} as iac does not exist")
            continue

        deployment_stacks.append(
            StackDeploymentRequest(
                stack_name=app.app_id,
                iac=iac,
                pulumi_config={},
                deployment_id=deployment_id,
            )
        )

    order, results = await run_concurrent_destroys(
        user_pack.region,
        user_pack.assumed_role_arn,
        deployment_stacks,
        user_pack.id,
        tmp_dir,
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


async def tear_down_pack(
    pack_id: str,
    deployment_id: str,
):
    logger.info(f"Tearing down pack {pack_id}")
    iac_storage = get_iac_storage()
    user_pack = UserPack.get(pack_id)

    logger.info(f"Destroying app stacks")

    with TempDir() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        await destroy_applications(user_pack, iac_storage, deployment_id, tmp_dir)

        common_version = user_pack.apps.get(UserPack.COMMON_APP_NAME, 0)
        if common_version == 0:
            raise ValueError("Common stack not found")

        common_pack = UserApp.get(
            UserApp.composite_key(user_pack.id, UserPack.COMMON_APP_NAME),
            common_version,
        )
        await destroy_common_stack(
            user_pack, common_pack, iac_storage, deployment_id, tmp_dir
        )
