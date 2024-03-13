import asyncio
from pathlib import Path
from typing import Tuple

from aiomultiprocess import Pool
from pulumi import automation as auto

from src.dependencies.injection import get_iac_storage
from src.deployer.deploy import DeploymentResult, StackDeploymentRequest
from src.deployer.models.deployment import (
    Deployment,
    DeploymentAction,
    DeploymentStatus,
    PulumiStack,
)
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.stack_pack.models.user_app import AppLifecycleStatus, UserApp
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.storage.iac_storage import IaCDoesNotExistError, IacStorage
from src.util.logging import logger
from src.util.tmp import TempDir


async def run_destroy(
    region: str,
    assume_role_arn: str,
    project_name: str,
    app_name: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    deployment_id: str,
    tmp_dir: Path,
) -> DeploymentResult:
    pulumi_stack = PulumiStack(
        project_name=project_name,
        name=PulumiStack.sanitize_stack_name(app_name),
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
    try:
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
    except Exception as e:
        pulumi_stack.update(
            actions=[
                PulumiStack.status.set(DeploymentStatus.FAILED.value),
                PulumiStack.status_reason.set(str(e)),
            ]
        )
        deployment.update(
            actions=[
                Deployment.status.set(DeploymentStatus.FAILED.value),
                Deployment.status_reason.set(str(e)),
            ]
        )
        return DeploymentResult(
            manager=None,
            status=DeploymentStatus.FAILED,
            reason=str(e),
            stack=pulumi_stack,
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
                    stack.project_name,
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
    common_pack.transition_status(
        DeploymentStatus.IN_PROGRESS, DeploymentAction.DESTROY, "Tearing down"
    )
    order, results = await run_concurrent_destroys(
        user_pack.region,
        user_pack.assumed_role_arn,
        [
            StackDeploymentRequest(
                project_name=common_pack.get_pack_id(),
                stack_name=common_pack.get_app_name(),
                iac=iac,
                pulumi_config={},
                deployment_id=deployment_id,
            )
        ],
        user_pack.id,
        tmp_dir,
    )
    common_pack.transition_status(
        results[0].status, DeploymentAction.DESTROY, results[0].reason
    )
    actions = [UserApp.deployments.add({deployment_id})]
    if results[0].status == DeploymentStatus.SUCCEEDED:
        actions.append(UserApp.iac_stack_composite_key.set(None))
    common_pack.update(actions=actions)


async def destroy_applications(
    user_pack: UserPack,
    iac_storage: IacStorage,
    deployment_id: str,
    tmp_dir: Path,
) -> bool:
    deployment_stacks: list[StackDeploymentRequest] = []
    apps: dict[str, UserApp] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get_latest_deployed_version(
            UserApp.composite_key(user_pack.id, name)
        )
        if app == None:
            # this would mean that nothing has been deployed
            continue
        app.transition_status(
            DeploymentStatus.IN_PROGRESS, DeploymentAction.DESTROY, "Tearing down"
        )
        apps[app.get_app_name()] = app
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
                project_name=app.get_pack_id(),
                stack_name=app.get_app_name(),
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
    success = True
    for i, name in enumerate(order):
        app = apps[name]
        result = results[i]
        success = success and result.status == DeploymentStatus.SUCCEEDED
        app.transition_status(result.status, DeploymentAction.DESTROY, result.reason)
        actions = [UserApp.deployments.add({deployment_id})]
        if results[0].status == DeploymentStatus.SUCCEEDED:
            actions.append(UserApp.iac_stack_composite_key.set(None))
        app.update(actions=actions)
    return success


async def tear_down_user_app(
    pack: UserPack,
    app: UserApp,
    iac_storage: IacStorage,
    deployment_id: str,
    tmp_dir: Path,
):
    logger.info(f"Tearing down app {app.app_id}")
    app.transition_status(
        DeploymentStatus.IN_PROGRESS, DeploymentAction.DESTROY, "Tearing down"
    )
    _, results = await run_concurrent_destroys(
        pack.region,
        pack.assumed_role_arn,
        [
            StackDeploymentRequest(
                project_name=pack.id,
                stack_name=app.get_app_name(),
                iac=iac_storage.get_iac(pack.id, app.get_app_name(), app.version),
                pulumi_config={},
                deployment_id=deployment_id,
            )
        ],
        pack.id,
        tmp_dir,
    )

    result = results[0]
    app.transition_status(result.status, DeploymentAction.DESTROY, result.reason)
    actions = [UserApp.deployments.add({deployment_id})]
    if results[0].status == DeploymentStatus.SUCCEEDED:
        actions.append(UserApp.iac_stack_composite_key.set(None))
    app.update(actions=actions)


async def tear_down_single(pack: UserPack, app: UserApp, deployment_id: str):
    iac_storage = get_iac_storage()
    with TempDir() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        await tear_down_user_app(pack, app, iac_storage, deployment_id, tmp_dir)
        common_pack = UserApp.get_latest_deployed_version(
            UserApp.composite_key(pack.id, UserPack.COMMON_APP_NAME),
        )
        await destroy_common_stack(
            pack, common_pack, iac_storage, deployment_id, tmp_dir
        )
        pack.update(actions=[UserPack.tear_down_in_progress.set(False)])


async def tear_down_pack(
    pack_id: str,
    deployment_id: str,
):
    logger.info(f"Tearing down pack {pack_id}")
    iac_storage = get_iac_storage()
    user_pack = UserPack.get(pack_id)
    user_pack.update(actions=[UserPack.tear_down_in_progress.set(True)])

    logger.info(f"Destroying app stacks")

    with TempDir() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        common_version = user_pack.apps.get(UserPack.COMMON_APP_NAME, 0)
        if common_version == 0:
            raise ValueError("Common stack not found")

        common_pack = UserApp.get(
            UserApp.composite_key(user_pack.id, UserPack.COMMON_APP_NAME),
            common_version,
        )
        common_pack.update(
            actions=[
                UserApp.status.set(AppLifecycleStatus.PENDING.value),
                UserApp.status_reason.set("waiting for applications to be destroyed"),
            ]
        )

        success = await destroy_applications(
            user_pack, iac_storage, deployment_id, tmp_dir
        )

        if not success:
            common_pack.transition_status(
                DeploymentStatus.FAILED,
                DeploymentAction.DESTROY,
                "One or more applications failed to destroy",
            )
            return

        await destroy_common_stack(
            user_pack, common_pack, iac_storage, deployment_id, tmp_dir
        )
        user_pack.update(actions=[UserPack.tear_down_in_progress.set(False)])
