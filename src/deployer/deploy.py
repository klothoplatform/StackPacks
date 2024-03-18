import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from aiomultiprocess import Pool
from pydantic import BaseModel

from pulumi import automation as auto
from src.dependencies.injection import (
    get_binary_storage,
    get_iac_storage,
    get_ses_client,
)
from src.deployer.models.deployment import (
    Deployment,
    DeploymentAction,
    DeploymentStatus,
    PulumiStack,
)
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.pulumi.manager import AppManager, LiveState
from src.engine_service.binaries.fetcher import BinaryStorage, Binary
from src.stack_pack import ConfigValues, StackPack, get_stack_packs
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.models.user_app import AppLifecycleStatus, UserApp
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.aws.ses import send_email
from src.util.logging import logger
from src.util.tmp import TempDir


@dataclass
class DeploymentResult:
    manager: AppManager | None
    status: DeploymentStatus
    reason: str
    stack: PulumiStack | None


class StackDeploymentRequest(BaseModel):
    deployment_id: str
    project_name: str
    stack_name: str
    # iac: bytes
    pulumi_config: dict[str, str]


PROJECT_NAME = "StackPack"


async def build_and_deploy(
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
    try:
        pulumi_stack.save()
        deployment.save()
        builder = AppBuilder(tmp_dir)
        stack = builder.prepare_stack(iac, pulumi_stack)
        builder.configure_aws(stack, assume_role_arn, region)
        for k, v in pulumi_config.items():
            stack.set_config(k, auto.ConfigValue(v, secret=True))
        deployer = AppDeployer(
            stack,
            DeploymentDir(user, deployment_id),
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
    except Exception as e:
        logger.error(f"Error deploying {app_name}: {e}", exc_info=True)
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
            reason="Internal error",
            stack=None,
        )


async def build_and_deploy_application(
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
    app = UserApp.get(UserApp.composite_key(pack_id, app_name), pack.apps[app_name])
    iac = iac_storage.get_iac(
        pack.id, app.get_app_name(), pack.apps[app.get_app_name()]
    )
    app.transition_status(
        DeploymentStatus.IN_PROGRESS, DeploymentAction.DEPLOY, "Deployment in progress"
    )
    result = await build_and_deploy(
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
    iac_composite_key = result.stack.composite_key() if result.stack else None
    app.update(
        actions=[
            UserApp.iac_stack_composite_key.set(iac_composite_key),
            UserApp.deployments.add({deployment_id}),
        ]
    )
    app.transition_status(result.status, DeploymentAction.DEPLOY, result.reason)
    logger.info(f"Deployment of {app.get_app_name()} complete. Status: {result.status}")
    return result


async def run_concurrent_deployments(
    stacks: list[StackDeploymentRequest],
    user: str,
    tmp_dir: Path,
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
                build_and_deploy_application,
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


async def rerun_pack_with_live_state(
    user_pack: UserPack,
    common_pack: UserApp,
    common_stack: CommonStack,
    iac_storage: IacStorage,
    binary_storage: BinaryStorage,
    live_state: LiveState,
    sps: dict[str, StackPack],
    tmp_dir: str,
):
    logger.info(f"Rerunning pack {user_pack.id} with imports")

    configuration: dict[str, ConfigValues] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get(UserApp.composite_key(user_pack.id, name), version)
        configuration[name] = app.get_configurations()

    await user_pack.run_pack(
        stack_packs=sps,
        config=configuration,
        tmp_dir=tmp_dir,
        iac_storage=iac_storage,
        binary_storage=binary_storage,
        increment_versions=False,
        imports=live_state.to_constraints(common_stack, common_pack.configuration),
    )


async def deploy_applications(
    user_pack: UserPack,
    sps: dict[str, StackPack],
    deployment_id: str,
    tmp_dir: Path,
) -> bool:
    deployment_stacks: list[StackDeploymentRequest] = []
    apps: dict[str, UserApp] = {}
    for name, version in user_pack.apps.items():
        if name == UserPack.COMMON_APP_NAME:
            continue
        app = UserApp.get(UserApp.composite_key(user_pack.id, name), version)
        apps[app.get_app_name()] = app
        sp = sps[app.get_app_name()]
        pulumi_config = sp.get_pulumi_configs(app.get_configurations())
        deployment_stacks.append(
            StackDeploymentRequest(
                project_name=app.get_pack_id(),
                stack_name=app.get_app_name(),
                pulumi_config=pulumi_config,
                deployment_id=deployment_id,
            )
        )

    order, results = await run_concurrent_deployments(
        deployment_stacks,
        user_pack.id,
        tmp_dir,
    )
    return all(result.status == DeploymentStatus.SUCCEEDED for result in results)


async def deploy_app(
    pack: UserPack,
    app: UserApp,
    stack_pack: StackPack,
    deployment_id: str,
    tmp_dir: Path,
) -> DeploymentResult:
    pulumi_config = stack_pack.get_pulumi_configs(app.get_configurations())
    _, results = await run_concurrent_deployments(
        [
            StackDeploymentRequest(
                project_name=pack.id,
                stack_name=app.get_app_name(),
                pulumi_config=pulumi_config,
                deployment_id=deployment_id,
            )
        ],
        pack.id,
        tmp_dir,
    )

    return results[0]


async def deploy_single(
    pack: UserPack, app: UserApp, deployment_id: str, email: str = None
):
    sps = get_stack_packs()
    iac_storage = get_iac_storage()
    binary_storage = get_binary_storage()
    stack_pack = sps[app.get_app_name()]
    common_stack = CommonStack(list(sps.values()))
    common_app = UserApp.get(
        UserApp.composite_key(pack.id, UserPack.COMMON_APP_NAME),
        pack.apps[UserPack.COMMON_APP_NAME],
    )
    app.update(
        actions=[
            UserApp.status.set(AppLifecycleStatus.PENDING.value),
            UserApp.status_reason.set(
                f"Updating Common Resources, then deploying {app.get_app_name()}."
            ),
        ]
    )
    try:
        binary_storage.ensure_binary(Binary.IAC)

        with TempDir() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            result = await deploy_app(
                pack, common_app, common_stack, deployment_id, tmp_dir
            )
            if result.status == DeploymentStatus.FAILED:
                app.transition_status(
                    result.status, DeploymentAction.DEPLOY, result.reason
                )
                return
            live_state = await result.manager.read_deployed_state()
            _ = await app.run_app(
                stack_pack=stack_pack,
                dir=str(tmp_dir),
                iac_storage=iac_storage,
                binary_storage=binary_storage,
                imports=live_state.to_constraints(
                    common_stack, common_app.get_configurations()
                ),
            )
            await deploy_app(pack, app, stack_pack, deployment_id, tmp_dir)
            if email is not None:
                send_email(get_ses_client(), email, sps.keys())
    except Exception as e:
        if app.status == AppLifecycleStatus.PENDING.value:
            app.transition_status(
                DeploymentStatus.FAILED, DeploymentAction.DEPLOY, str(e)
            )


async def deploy_pack(
    pack_id: str, sps: dict[str, StackPack], deployment_id: str, email: str | None
):
    with TempDir() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        logger.info(f"Deploying pack {pack_id}")
        iac_storage = get_iac_storage()
        binary_storage = get_binary_storage()
        user_pack = UserPack.get(pack_id)
        if user_pack.tear_down_in_progress:
            raise ValueError("Pack is currently being torn down")

        common_version = user_pack.apps.get(UserPack.COMMON_APP_NAME, 0)
        if common_version == 0:
            raise ValueError("Common stack not found")

        common_pack = UserApp.get(
            UserApp.composite_key(user_pack.id, UserPack.COMMON_APP_NAME),
            common_version,
        )
        common_stack = CommonStack(list(sps.values()))

        for app_name, version in user_pack.apps.items():
            if app_name == UserPack.COMMON_APP_NAME:
                continue
            app = UserApp.get(UserApp.composite_key(pack_id, app_name), version)
            app.update(
                actions=[
                    UserApp.status.set(AppLifecycleStatus.PENDING.value),
                    UserApp.status_reason.set(
                        f"Updating Common Resources, then deploying {app_name}."
                    ),
                ]
            )
        try:

            logger.info(f"Deploying common stack")
            binary_storage.ensure_binary(Binary.IAC)

            result = await deploy_app(
                user_pack,
                common_pack,
                common_stack,
                deployment_id,
                tmp_dir,
            )

            if result.status == DeploymentStatus.FAILED:
                for app_name, version in user_pack.apps.items():
                    if app_name == UserPack.COMMON_APP_NAME:
                        continue
                    app = UserApp.get(UserApp.composite_key(pack_id, app_name), version)
                    app.transition_status(
                        DeploymentStatus.FAILED, DeploymentAction.DEPLOY, result.reason
                    )
                return

            live_state = await result.manager.read_deployed_state()

            logger.info(f"Rerunning pack with live state")
            await rerun_pack_with_live_state(
                user_pack,
                common_pack,
                common_stack,
                iac_storage,
                binary_storage,
                live_state,
                sps,
                tmp_dir_str,
            )

            logger.info(f"Deploying app stacks")
            sucess = await deploy_applications(user_pack, sps, deployment_id, tmp_dir)
            if email is not None and sucess:
                send_email(get_ses_client(), email, sps.keys())
        except Exception as e:
            for app_name, version in user_pack.apps.items():
                if app_name == UserPack.COMMON_APP_NAME:
                    continue
                app = UserApp.get(UserApp.composite_key(pack_id, app_name), version)
                if app.status == AppLifecycleStatus.PENDING.value:
                    app.transition_status(
                        DeploymentStatus.FAILED, DeploymentAction.DEPLOY, str(e)
                    )
            logger.error(f"Error deploying pack {pack_id}: {e}")
            raise e
