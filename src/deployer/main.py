import asyncio
from dataclasses import dataclass
from typing import Dict
from fastapi import Request
from pydantic import BaseModel
from src.deployer.pulumi.manager import AppManager
from src.deployer.models.deployment import (
    DeploymentStatus,
    PulumiStack,
)
from src.util.logging import logger
from multiprocessing import Queue
from queue import Empty

# This would be a dictionary, database, or some other form of storage in a real application
deployments: Dict[str, Queue] = {}
PROJECT_NAME = "StackPack"


@dataclass
class DeploymentResult:
    manager: AppManager | None
    status: DeploymentStatus
    reason: str
    stack: PulumiStack | None

class StackDeploymentRequest(BaseModel):
    stack_name: str
    iac: bytes
    pulumi_config: dict[str, str]


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
