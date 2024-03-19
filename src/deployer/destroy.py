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
from src.stack_pack.storage.iac_storage import IaCDoesNotExistError
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


async def run_destroy_application(
    pack_id: str,
    app_name: str,
    user: str,
    pulumi_config: dict[str, str],
    deployment_id: str,
    tmp_dir: Path,
) -> DeploymentResult:
    logger.info(
        f"Building and deploying {app_name} for pack {pack_id} with deployment id {deployment_id}"
    )
    iac_storage = get_iac_storage()
    pack = UserPack.get(pack_id)
    app = UserApp.get_latest_deployed_version(UserApp.composite_key(pack_id, app_name))
    if app is None:
        logger.info(f"Skipping destroy for {app_name} as it is not deployed")
        return DeploymentResult(
            manager=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="Not deployed",
            stack=None,
        )
    try:
        iac = iac_storage.get_iac(pack.id, app.get_app_name(), app.version)
    except IaCDoesNotExistError:
        # This state could happen if an application's iac failed to generate.
        # Since other applications and the common stack could have been deployed
        # don't fail the destroy process, just log and continue.
        logger.info(f"Skipping destroy for {app.app_id} as iac does not exist")
        return DeploymentResult(
            manager=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="IaC does not exist",
            stack=None,
        )
    app.transition_status(
        DeploymentStatus.IN_PROGRESS, DeploymentAction.DESTROY, "Destroy in progress"
    )
    result = await run_destroy(
        pack.region,
        pack.assumed_role_arn,
        pack.id,
        app.get_app_name(),
        user,
        iac,
        pulumi_config,
        deployment_id,
        tmp_dir / app.get_app_name(),
    )
    iac_composite_key = (
        result.stack.composite_key()
        if result.status != DeploymentStatus.SUCCEEDED
        else None
    )

    app.update(
        actions=[
            UserApp.outputs.set({}),
            UserApp.iac_stack_composite_key.set(iac_composite_key),
            UserApp.deployments.add({deployment_id}),
        ]
    )
    app.transition_status(result.status, DeploymentAction.DESTROY, result.reason)
    logger.info(f"DESTROY of {app.get_app_name()} complete. Status: {result.status}")
    return result


async def run_concurrent_destroys(
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
                run_destroy_application,
                args=(
                    stack.project_name,
                    stack.stack_name,
                    user,
                    stack.pulumi_config,
                    stack.deployment_id,
                    tmp_dir,
                ),
            )
            app_order.append(stack.stack_name)
            tasks.append(task)

        gathered = await asyncio.gather(*tasks)
        logger.info(f"Tasks: {tasks}")
        return app_order, gathered


async def destroy_applications(
    user_pack: UserPack,
    deployment_id: str,
    tmp_dir: Path,
) -> bool:
    deployment_stacks: list[StackDeploymentRequest] = []
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        deployment_stacks.append(
            StackDeploymentRequest(
                project_name=user_pack.id,
                stack_name=name,
                pulumi_config={},
                deployment_id=deployment_id,
            )
        )

    order, results = await run_concurrent_destroys(
        deployment_stacks,
        user_pack.id,
        tmp_dir,
    )

    return all(result.status == DeploymentStatus.SUCCEEDED for result in results)


async def tear_down_user_app(
    pack: UserPack,
    app: UserApp,
    deployment_id: str,
    tmp_dir: Path,
) -> DeploymentResult:
    logger.info(f"Tearing down app {app.app_id}")
    _, results = await run_concurrent_destroys(
        [
            StackDeploymentRequest(
                project_name=pack.id,
                stack_name=app.get_app_name(),
                pulumi_config={},
                deployment_id=deployment_id,
            )
        ],
        pack.id,
        tmp_dir,
    )
    return results[0]


async def tear_down_single(pack: UserPack, app: UserApp, deployment_id: str):
    with TempDir() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        result = await tear_down_user_app(pack, app, deployment_id, tmp_dir)

        if pack.tear_down_in_progress and result.status == DeploymentStatus.SUCCEEDED:
            common_pack = UserApp.get_latest_deployed_version(
                UserApp.composite_key(pack.id, UserPack.COMMON_APP_NAME),
            )
            await tear_down_user_app(pack, common_pack, deployment_id, tmp_dir)
            pack.update(actions=[UserPack.tear_down_in_progress.set(False)])


async def tear_down_pack(
    pack_id: str,
    deployment_id: str,
):
    logger.info(f"Tearing down pack {pack_id}")
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

        success = await destroy_applications(user_pack, deployment_id, tmp_dir)

        if not success:
            common_pack.transition_status(
                DeploymentStatus.FAILED,
                DeploymentAction.DESTROY,
                "One or more applications failed to destroy",
            )
            return

        await tear_down_user_app(user_pack, common_pack, deployment_id, tmp_dir)
        user_pack.update(actions=[UserPack.tear_down_in_progress.set(False)])
