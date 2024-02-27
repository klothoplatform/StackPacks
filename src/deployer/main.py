import asyncio
from contextlib import asynccontextmanager
from typing import Dict
from typing import List
import uuid
from fastapi import Request
from pydantic import BaseModel
from src.dependencies.injection import create_sts_client
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.models.deployment import (
    DeploymentStatus,
    Deployment,
    DeploymentAction,
    PulumiStack,
)
from src.util.logging import logger
from multiprocessing import Queue
from queue import Empty


# This would be a dictionary, database, or some other form of storage in a real application
deployments: Dict[str, Queue] = {}
PROJECT_NAME = "StackPack"


async def build_and_deploy(
    q: Queue,
    region: str,
    assume_role_arn: str,
    user: str,
    iac: bytes,
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
    builder = AppBuilder(create_sts_client())
    stack = builder.prepare_stack(iac, pulumi_stack)
    builder.configure_aws(stack, assume_role_arn, region)
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
):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    new_loop.run_until_complete(build_and_deploy(q, region, assume_role_arn, user, iac))
    new_loop.close()


async def run_destroy(
    q: Queue,
    region: str,
    assume_role_arn: str,
    user: str,
    iac: bytes,
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
    builder = AppBuilder(create_sts_client())
    stack = builder.prepare_stack(iac, pulumi_stack)
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
):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    new_loop.run_until_complete(run_destroy(q, region, assume_role_arn, user, iac))
    new_loop.close()


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
