from typing import Optional
from fastapi import APIRouter
from fastapi import Request

from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from src.dependencies.injection import get_iac_storage
from src.auth.token import get_user_id

from src.util.logging import logger

from src.stack_pack.models.user_pack import UserPack, UserStack
from src.stack_pack import ConfigValues, get_stack_packs, StackConfig
from src.util.tmp import TempDir

router = APIRouter()


class StackRequest(BaseModel):
    configuration: dict[str, ConfigValues]


class StackResponse(BaseModel):
    stack: UserStack
    policy: Optional[str] = None


@router.post("/api/stack")
async def create_stack(
    request: Request,
    body: StackRequest,
) -> StackResponse:
    policy: str = None
    user_id = await get_user_id(request)
    user_pack = UserPack(
        id=user_id,
        owner=user_id,
        configuration=body.configuration,
        created_by=user_id,
    )
    stack_packs = get_stack_packs()
    with TempDir() as tmp_dir:
        policy, _ = await user_pack.run_pack(stack_packs, get_iac_storage(), tmp_dir)
    user_pack.save()
    return {"stack": user_pack.to_user_stack(), "policy": policy}


class UpdateStackRequest(BaseModel):
    configuration: dict[str, ConfigValues] = None
    assume_role_arn: str = None
    region: str = None


@router.patch("/api/stack")
async def update_stack(
    request: Request,
    body: UpdateStackRequest,
) -> StackResponse:
    policy: str = None
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id, user_id)
    actions = []
    if body.assume_role_arn:
        actions.append(UserPack.assumed_role_arn.set(body.assume_role_arn))
    if body.region:
        # TODO: add check to see if they have already deployed a stack and its running, if so send back a 400 since we cant change region
        actions.append(UserPack.region.set(body.region))
    if body.configuration:
        actions.append(UserPack.configuration.set(body.configuration))
    if len(actions) > 0:
        user_pack.update(actions=actions)

    if body.configuration:
        stack_packs = get_stack_packs()
        with TempDir() as tmp_dir:
            policy, _ = await user_pack.run_pack(
                stack_packs, get_iac_storage(), tmp_dir
            )

    return {"stack": user_pack.to_user_stack(), "policy": policy}


@router.get("/api/stack")
async def my_stack(request: Request) -> UserStack:
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id, user_id)
    return user_pack.to_user_stack()


@router.get("/api/stackpacks")
async def list_stackpacks():
    sps = get_stack_packs()

    def config_to_dict(cfg: StackConfig):
        c = {
            "name": cfg.name,
            "description": cfg.description,
            "type": cfg.type,
        }
        if cfg.default is not None:
            c["default"] = cfg.default
        if cfg.validation is not None:
            c["validation"] = cfg.validation
        if cfg.pulumi_key is not None:
            c["pulumi_key"] = cfg.pulumi_key
        return c

    return {
        spid: {
            "name": sp.name,
            "version": sp.version,
            "configuration": {
                k: config_to_dict(cfg) for k, cfg in sp.configuration.items()
            },
        }
        for spid, sp in sps.items()
    }
