from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.dependencies.injection import get_ses_client
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
    send_klotho_engineering_email(get_ses_client(), request)
    return
