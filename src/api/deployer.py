from asyncio import Queue
from multiprocessing import Process
from fastapi import APIRouter
from fastapi import Request

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.auth.token import get_user_id

from src.util.logging import logger
from src.deployer.main import (
    deployments,
    run_build_and_deploy,
    run_destroy_loop,
    stream_deployment_events,
)

router = APIRouter()


class DeploymentRequest(BaseModel):
    region: str
    assume_role_arn: str
    packages: list[str]


def read_zip_to_bytes(zip_file_path):
    with open(zip_file_path, "rb") as file:
        return file.read()


@router.post("/api/install")
async def install(
    request: Request,
    body: DeploymentRequest,
):
    iac = read_zip_to_bytes(
        "/Users/jordansinger/workspace/StackPacks/untitled_architecture_default (2).zip"
    )

    user_id = await get_user_id(request)
    # Create a new queue for this deployment
    deployment_id = f"{user_id}"
    q = Queue()
    deployments[deployment_id] = q
    p = Process(
        target=run_build_and_deploy,
        args=(q, body.region, body.assume_role_arn, user_id, iac),
    )
    p.start()
    # Start the deployment in the background

    return {"message": "Deployment started"}


@router.post("/api/tear_down")
async def tear_down(
    request: Request,
    body: DeploymentRequest,
):
    iac = read_zip_to_bytes(
        "/Users/jordansinger/workspace/StackPacks/untitled_architecture_default (2).zip"
    )
    user_id = await get_user_id(request)

    # Create a new queue for this deployment
    deployment_id = f"{user_id}"
    q = Queue()
    deployments[deployment_id] = q

    logger.info(f"Starting destroy for {deployment_id}")
    p = Process(
        target=run_destroy_loop,
        args=(q, body.region, body.assume_role_arn, user_id, iac),
    )
    p.start()
    # start destroy in the background

    return {"message": "Destroy started"}


@router.get("/api/install/{id}/logs")
async def stream_deployment_logs(request: Request, id: str):
    return StreamingResponse(
        stream_deployment_events(request, id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-buffer"},
    )
