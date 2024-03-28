from fastapi import APIRouter, Request
from pydantic import BaseModel
from pynamodb.exceptions import DoesNotExist

from src.auth.token import AuthError
from src.dependencies.injection import get_ses_client
from src.stack_pack.models.project import Project
from src.util.aws.ses import send_klotho_engineering_email
from src.util.logging import logger

router = APIRouter()


class HealthRequest(BaseModel):
    OldStateValue: str
    NewStateValue: str
    AlarmArn: str
    StateChangeTime: str
    PackId: str


@router.post("/api/health")
async def create_stack(
    request: Request,
    body: HealthRequest,
):
    logger.info(f"Received health check request: {body}")
    try:
        project = Project.get(body.PackId)
    except DoesNotExist:
        logger.error(f"User pack not found for pack_id: {body.PackId}")
        raise AuthError("Unauthorized Project for health reporting")
    if body.NewStateValue != "OK":
        send_klotho_engineering_email(get_ses_client(), body.model_dump())
    return
