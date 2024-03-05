import asyncio

from aiomultiprocess import Worker
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.auth.token import get_user_id
from src.deployer.deploy import deploy_pack
from src.deployer.destroy import tear_down_pack
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.stack_pack import get_stack_packs
from src.util.logging import logger

router = APIRouter()


def read_zip_to_bytes(zip_file_path):
    with open(zip_file_path, "rb") as file:
        return file.read()


@router.post("/api/install")
async def install(
    request: Request,
):
    user_id = await get_user_id(request)
    stack_packs = get_stack_packs()

    worker = Worker(target=deploy_pack, args=(user_id, stack_packs))
    worker.start()

    deploy_dir = DeploymentDir(user_id)
    log = deploy_dir.get_log("stack", "up", deployment_id)

    try:
        tail = await asyncio.wait_for(log.tail_wait_created(), timeout=60)
    except asyncio.TimeoutError:
        logger.warning("Log file not created after 60 seconds")
        return JSONResponse(
            content={"message": "Deployment created"},
            status_code=201,
            headers={"Location": f"/api/install/{deployment_id}/logs"},
        )

    return StreamingResponse(
        tail,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-buffer"},
    )


@router.post("/api/tear_down")
async def tear_down(
    request: Request,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)

    worker = Worker(target=tear_down_pack, args=(user_id))
    worker.start()

    deploy_dir = DeploymentDir(user_id)
    log = deploy_dir.get_log("stack", "destroy", deployment_id)

    try:
        tail = await asyncio.wait_for(log.tail_wait_created(), timeout=60)
    except asyncio.TimeoutError:
        logger.warning("Log file not created after 60 seconds")
        return JSONResponse(
            content={"message": "Tear down started"},
            status_code=201,
            headers={"Location": f"/api/install/{deployment_id}/logs"},
        )

    return StreamingResponse(
        tail,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-buffer"},
    )


@router.get("/api/install/{deploy_id}/logs")
async def stream_deployment_logs(request: Request, deploy_id: str):
    user_id = await get_user_id(request)
    deploy_dir = DeploymentDir(user_id)
    log = deploy_dir.get_log("stack", "destroy", deploy_id)
    if not log.path.exists():
        log = deploy_dir.get_log("stack", "up", deploy_id)
    return StreamingResponse(
        await log.tail_wait_created(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-buffer"},
    )
