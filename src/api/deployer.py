import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from src.auth.token import get_email, get_user_id
from src.deployer.deploy import deploy_pack, deploy_single
from src.deployer.destroy import tear_down_pack, tear_down_single
from src.deployer.models.deployment import PulumiStack
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.stack_pack import get_stack_packs
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack

router = APIRouter()


@router.post("/api/install")
async def install(
    request: Request,
    background_tasks: BackgroundTasks,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)
    users_email = await get_email(request)
    stack_packs = get_stack_packs()

    if deployment_id is None:
        deployment_id = str(uuid.uuid4())
    elif deployment_id == "latest":
        return Response(status_code=400, content="latest is a reserved deployment_id")

    background_tasks.add_task(
        deploy_pack, user_id, stack_packs, deployment_id, users_email
    )

    return JSONResponse(
        status_code=201,
        content={"message": "Deployment started", "deployment_id": deployment_id},
    )


@router.post("/api/install/{app_name}")
async def install_app(
    request: Request,
    background_tasks: BackgroundTasks,
    app_name: str,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)
    users_email = await get_email(request)

    if deployment_id is None:
        deployment_id = str(uuid.uuid4())
    elif deployment_id == "latest":
        return Response(status_code=400, content="latest is a reserved deployment_id")

    user_pack = UserPack.get(user_id)
    if user_pack.tear_down_in_progress:
        return HTTPException(
            status_code=400,
            detail="Tear down in progress",
        )
    app = UserApp.get_latest_version(UserApp.composite_key(user_id, app_name))

    background_tasks.add_task(deploy_single, user_pack, app, deployment_id, users_email)

    return JSONResponse(
        status_code=201,
        content={"message": "Deployment started", "deployment_id": deployment_id},
    )


@router.post("/api/tear_down")
async def tear_down(
    request: Request,
    background_tasks: BackgroundTasks,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)

    if deployment_id is None:
        deployment_id = str(uuid.uuid4())
    elif deployment_id == "latest":
        return Response(status_code=400, content="latest is a reserved deployment_id")

    background_tasks.add_task(tear_down_pack, user_id, deployment_id)

    return JSONResponse(
        status_code=201,
        content={"message": "Destroy started", "deployment_id": deployment_id},
    )


@router.post("/api/tear_down/{app_name}")
async def tear_down_app(
    request: Request,
    background_tasks: BackgroundTasks,
    app_name: str,
    deployment_id: str = None,
):
    user_id = await get_user_id(request)

    if deployment_id is None:
        deployment_id = str(uuid.uuid4())
    elif deployment_id == "latest":
        return Response(status_code=400, content="latest is a reserved deployment_id")

    user_pack = UserPack.get(user_id)
    app = UserApp.get_latest_deployed_version(UserApp.composite_key(user_id, app_name))

    if (
        len(user_pack.apps) < 2
        or len(user_pack.apps) == 2
        and set(user_pack.apps.keys())
        == {
            UserPack.COMMON_APP_NAME,
            app_name,
        }
    ):
        user_pack.update(actions=[UserPack.tear_down_in_progress.set(True)])

    background_tasks.add_task(tear_down_single, user_pack, app, deployment_id)

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
