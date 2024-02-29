from fastapi import APIRouter
from fastapi import Request

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.auth.token import get_user_id

from src.util.logging import logger

from src.stack_pack import ConfigValues

router = APIRouter()


class StackRequest(BaseModel):
    stacks: dict[str, ConfigValues]


@router.post("/api/stack")
async def create_stack(
    request: Request,
    body: StackRequest,
):
    # TODO(js): render constraints, call engine -> get policy
    # call iac -> store in iac_storage
    pass


@router.patch("/api/stack")
async def update_stack(
    request: Request,
    body: StackRequest,
):
    # TODO(js): basically same as create_stack
    pass


@router.get("/api/stack")
async def my_stack():
    pass


@router.get("/api/stackpacks")
async def list_stackpacks():
    # TODO: gg
    pass
