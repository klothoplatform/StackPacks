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
from src.stack_pack import get_stack_packs
from src.stack_pack.models.user_pack import UserPack
from src.dependencies.injection import get_iac_storage
from src.util.tmp import TempDir

router = APIRouter()


def read_zip_to_bytes(zip_file_path):
    with open(zip_file_path, "rb") as file:
        return file.read()


@router.post("/api/install")
async def install(
    request: Request,
    regen: bool = False,
):
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id)
    store = get_iac_storage()

    tmp_dir = TempDir()
    if regen:
        logger.info("Regenerating iac for %s", user_pack.id)
        stack_packs = get_stack_packs()
        _, iac = await user_pack.run_pack(stack_packs, store, tmp_dir.dir)
    else:
        iac = store.get_iac(user_pack.id)

    sps = get_stack_packs()

    pulumi_config = {}
    for name, config in user_pack.configuration.items():
        sp = sps[name]
        pulumi_config.update(sp.get_pulumi_configs(config))

    # Create a new queue for this deployment
    deployment_id = f"{user_id}"
    q = Queue()
    deployments[deployment_id] = q
    p = Process(
        target=run_build_and_deploy,
        args=(
            q,
            user_pack.region,
            user_pack.assumed_role_arn,
            user_id,
            iac,
            pulumi_config,
            tmp_dir,
        ),
    )
    p.start()
    # Start the deployment in the background

    return {"message": "Deployment started"}


@router.post("/api/tear_down")
async def tear_down(
    request: Request,
):
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id)
    store = get_iac_storage()
    iac = store.get_iac(user_pack.id)

    sps = get_stack_packs()

    pulumi_config = {}
    for name, config in user_pack.configuration.items():
        sp = sps[name]
        pulumi_config.update(sp.get_pulumi_configs(config))

    # Create a new queue for this deployment
    deployment_id = f"{user_id}"
    q = Queue()
    deployments[deployment_id] = q

    logger.info(f"Starting destroy for {deployment_id}")
    p = Process(
        target=run_destroy_loop,
        args=(
            q,
            user_pack.region,
            user_pack.assumed_role_arn,
            user_id,
            iac,
            pulumi_config,
            TempDir(),
        ),
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
