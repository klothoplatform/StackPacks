from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from src.auth.token import AuthError
from src.util.logging import logger
from src.api.deployer import router as deployer_router
from src.api.stack_packs import router as stack_packs_router
from src.deployer.models.deployment import Deployment, PulumiStack
from src.stack_pack.models.user_pack import UserPack
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("DYNAMODB_HOST", None) is not None:
        Deployment.create_table(wait=True)
        PulumiStack.create_table(wait=True)
        UserPack.create_table(wait=True)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)

logger.debug("Starting API")

app.include_router(deployer_router)
app.include_router(stack_packs_router)


@app.get("/api/ping")
async def ping():
    return Response(status_code=204)


@app.exception_handler
def handle_auth_error(ex: AuthError):
    response = JSONResponse(content=ex.error, status_code=ex.status_code)
    return response
