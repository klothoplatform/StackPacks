import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from src.api.health_router import router as health_router
from src.api.project_router import router as projects_router
from src.api.stackpacks_router import router as stackpacks_router
from src.api.workflow_router import router as workflow_router
from src.auth.token import AuthError
from src.deployer.models.pulumi_stack import PulumiStack
from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.models.workflow_run import WorkflowRun
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from src.util.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("DYNAMODB_HOST", None) is not None:
        WorkflowRun.create_table(wait=True)
        WorkflowJob.create_table(wait=True)
        PulumiStack.create_table(wait=True)
        Project.create_table(wait=True)
        AppDeployment.create_table(wait=True)
    yield


app = FastAPI(lifespan=lifespan)

logger.debug("Starting API")

app.include_router(projects_router)
app.include_router(workflow_router)
app.include_router(stackpacks_router)
app.include_router(health_router)


@app.get("/api/ping")
async def ping():
    return Response(status_code=204)


@app.exception_handler
def handle_auth_error(ex: AuthError):
    response = JSONResponse(content=ex.error, status_code=ex.status_code)
    return response


@app.middleware("http")
async def detailed_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # only add exception info to requests in dev (via localhost)
        if request.client.host == "127.0.0.1":
            logger.warning(f"Exception in {request.url}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": str(e)})
        raise
