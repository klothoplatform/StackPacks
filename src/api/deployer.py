import uuid

from aiomultiprocess import Worker
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from src.auth.token import get_user_id
from src.deployer.deploy import deploy_pack
from src.deployer.destroy import tear_down_pack
from src.deployer.models.deployment import PulumiStack
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.stack_pack import get_stack_packs
from src.stack_pack.models.user_app import UserApp

router = APIRouter()


@router.post("/api/install")
async def install(
    request: Request,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)
    stack_packs = get_stack_packs()

    if deployment_id is None:
        deployment_id = str(uuid.uuid4())
    elif deployment_id == "latest":
        return Response(status_code=400, content="latest is a reserved deployment_id")

    worker = Worker(target=deploy_pack, args=(user_id, stack_packs, deployment_id))
    worker.start()

    return JSONResponse(
        status_code=201,
        content={"message": "Deployment started", "deployment_id": deployment_id},
    )


@router.post("/api/tear_down")
async def tear_down(
    request: Request,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)

    if deployment_id is None:
        deployment_id = str(uuid.uuid4())
    elif deployment_id == "latest":
        return Response(status_code=400, content="latest is a reserved deployment_id")

    worker = Worker(target=tear_down_pack, args=(user_id, deployment_id))
    worker.start()

    return JSONResponse(
        status_code=201,
        content={"message": "Destroy started", "deployment_id": deployment_id},
    )


@router.get("/api/install/{deploy_id}/{app_id}/logs")
async def stream_deployment_logs(request: Request, deploy_id: str, app_id: str):
    user_id = await get_user_id(request)
    deploy_dir = DeploymentDir(user_id, deploy_id)
    app_key = UserApp.composite_key(user_id, app_id)
    log = deploy_dir.get_log(PulumiStack.sanitize_stack_name(app_key))
    return StreamingResponse(
        log.tail(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-buffer"},
    )
