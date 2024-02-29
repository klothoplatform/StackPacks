from fastapi import APIRouter
from fastapi import Request

from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from src.dependencies.injection import get_iac_storage
from src.auth.token import get_user_id

from src.util.logging import logger

from src.stack_pack import ConfigValues, get_stack_packs
from src.stack_pack.models.user_pack import UserPack, UserStack

router = APIRouter()


class StackRequest(BaseModel):
    stacks: dict[str, ConfigValues]


@router.post("/api/stack")
async def create_stack(
    request: Request,
    body: StackRequest,
) -> UserStack:
    policy: str = None
    user_id = await get_user_id(request)
    user_pack = UserPack(
        id=user_id,
        owner=user_id,
        configuration=body.stacks,
        created_by=user_id,
    )
    stack_packs = get_stack_packs()
    policy = await user_pack.run_pack(stack_packs, get_iac_storage())
    user_pack.save()
    return {"stack": user_pack.to_user_stack(), "policy": policy}


class UpdateStackRequest(BaseModel):
    stacks: dict[str, ConfigValues] = None
    assume_role_arn: str = None
    region: str = None

@router.patch("/api/stack")
async def update_stack(
    request: Request,
    body: UpdateStackRequest,
) -> UserStack:
    policy: str = None
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id, user_id)
    actions = []
    if body.assume_role_arn:
        actions.append(UserPack.assumed_role_arn.set(body.assume_role_arn))
    if body.region:
        actions.append(UserPack.region.set(body.region))
    if body.stacks:
        actions.append(UserPack.configuration.set(body.stacks))
    if len(actions) > 0:
        user_pack.update(actions=actions)
        
    if body.stacks:
        stack_packs = get_stack_packs()
        policy = await user_pack.run_pack(stack_packs, get_iac_storage())
        
    return {"stack": user_pack.to_user_stack(), "policy": policy}


@router.get("/api/stack")
async def my_stack():
    pass


@router.get("/api/stackpacks")
async def list_stackpacks():
    # TODO: gg
    pass
