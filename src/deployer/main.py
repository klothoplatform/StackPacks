import asyncio
from typing import Dict
import uuid
import concurrent.futures
from fastapi import Request
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
from multiprocessing import Process, Queue
from queue import Empty
from src.util.tmp import TempDir


# This would be a dictionary, database, or some other form of storage in a real application
deployments: Dict[str, Queue] = {}
PROJECT_NAME = "StackPack"


async def build_and_deploy(
    q: Queue,
    region: str,
    assume_role_arn: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    tmp_dir: str,
):
    deployment_id = str(uuid.uuid4())
    pulumi_stack = PulumiStack(
        project_name=PROJECT_NAME,
        name=PulumiStack.sanitize_stack_name(user),
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
    builder = AppBuilder(tmp_dir)
    stack = builder.prepare_stack(iac, pulumi_stack)
    builder.configure_aws(stack, assume_role_arn, region)
    for k, v in pulumi_config.items():
        stack.set_config(k, auto.ConfigValue(v, secret=True))
    deployer = AppDeployer(
        stack,
    )
    result_status, reason = await deployer.deploy(q)
    await q.put("Done")
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


def run_build_and_deploy(
    q: Queue,
    region: str,
    assume_role_arn: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    tmp_dir: TempDir,
):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    new_loop.run_until_complete(
        build_and_deploy(
            q, region, assume_role_arn, user, iac, pulumi_config, tmp_dir.dir
        )
    )
    new_loop.close()
    tmp_dir.cleanup()


async def run_destroy(
    q: Queue,
    region: str,
    assume_role_arn: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    tmp_dir: str,
):
    deployment_id = str(uuid.uuid4())
    pulumi_stack = PulumiStack(
        project_name=PROJECT_NAME,
        name=PulumiStack.sanitize_stack_name(user),
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
    )
    result_status, reason = await deployer.destroy_and_remove_stack(q)
    await q.put("Done")
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


def run_destroy_loop(
    q: Queue,
    region: str,
    assume_role_arn: str,
    user: str,
    iac: bytes,
    pulumi_config: dict[str, str],
    tmp_dir: TempDir,
):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    new_loop.run_until_complete(
        run_destroy(q, region, assume_role_arn, user, iac, pulumi_config, tmp_dir.dir)
    )
    new_loop.close()
    tmp_dir.cleanup()


class StackDeploymentRequest:
    stack_name: str
    iac: bytes
    pulumi_config: dict[str, str]


async def run_concurrent_deployments(
    q: Queue,
    region: str,
    assume_role_arn: str,
    stacks: list[StackDeploymentRequest],
    user: str,
):
    async def run_blocking_task_in_process(executor, task, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, task, *args)

    executor = concurrent.futures.ProcessPoolExecutor()

    # Start all tasks and get Future objects
    futures = [
        run_blocking_task_in_process(
            executor,
            run_build_and_deploy,
            q,
            region,
            assume_role_arn,
            user,
            stack.iac,
            stack.pulumi_config,
        )
        for stack in stacks
    ]

    # Return immediately without waiting for the tasks to complete
    return "Started tasks"


async def stream_deployment_events(request: Request, id: str):
    deployment_id = f"{id}"
    q = None
    while True:
        if q is None:
            if deployment_id not in deployments:
                logger.info(f"Deployment {deployment_id} not found")
                await asyncio.sleep(1)
                continue
            q = deployments[deployment_id]
        if await request.is_disconnected():
            logger.debug("Request disconnected")
            break
        try:
            result = q.get_nowait()
            if result == "Done":
                logger.info(f"Deployment {deployment_id} is done")
                return
        except Empty:
            await asyncio.sleep(0.25)  # Wait a bit before trying again
            continue
        yield f"data: {result}\n\n"
        return
