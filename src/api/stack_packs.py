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
async def create_stack():
    pass


@router.patch("/api/stack/{id}")
async def update_stack():
    pass


@router.get("/api/stack/{id}?version={version}")
async def get_stack():
    pass


@router.get("/api/stacks")
async def list_stacks():
    pass


@router.get("/api/applications")
async def list_applications():
    pass
