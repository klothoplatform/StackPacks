from asyncio import Queue
import asyncio
from multiprocessing import Process
from fastapi import APIRouter
from fastapi import Request, BackgroundTasks
import concurrent.futures
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.auth.token import get_user_id

from src.util.logging import logger
from src.deployer.main import (
    tear_down_pack,
    deploy_pack,
    stream_deployment_events,
)
from src.stack_pack import get_stack_packs
from aiomultiprocess import Worker

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
        
    return {"message": "Deployment started"}



@router.post("/api/tear_down")
async def tear_down(
    request: Request,
):
    user_id = await get_user_id(request)

    worker = Worker(target=tear_down_pack, args=(user_id))
    worker.start()

    return {"message": "Destroy started"}


@router.get("/api/install/{id}/logs")
async def stream_deployment_logs(request: Request, id: str):
    return StreamingResponse(
        stream_deployment_events(request, id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-buffer"},
    )
