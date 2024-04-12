import uuid
from typing import Optional

import jsons
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sse_starlette import EventSourceResponse
from starlette.responses import Response, StreamingResponse

from src.api.models.workflow_models import WorkflowRunSummary, WorkflowRunView
from src.auth.token import get_email, get_user_id
from src.deployer.deploy import (
    execute_deploy_single_workflow,
    execute_deployment_workflow,
)
from src.deployer.destroy import (
    execute_destroy_all_workflow,
    execute_destroy_single_workflow,
)
from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.models.workflow_run import WorkflowRun, WorkflowType
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from src.util.logging import logger

router = APIRouter()


@router.post("/api/project/workflows/install")
async def install(
    request: Request,
    background_tasks: BackgroundTasks,
):
    user_id = await get_user_id(request)
    users_email = await get_email(request)
    run = WorkflowRun.create(
        project_id=user_id,
        workflow_type=WorkflowType.DEPLOY,
        initiated_by=user_id,
        notification_email=users_email,
    )

    background_tasks.add_task(execute_deployment_workflow, run)

    return Response(
        media_type="application/json",
        status_code=201,
        content=jsons.dumps(WorkflowRunSummary.from_workflow_run(run).dict()),
    )


@router.post("/api/project/apps/{app_id}/workflows/install")
async def install_app(
    request: Request,
    background_tasks: BackgroundTasks,
    app_id: str,
):
    user_id = await get_user_id(request)
    users_email = await get_email(request)

    project = Project.get(user_id)
    if project.destroy_in_progress:
        return HTTPException(
            status_code=400,
            detail="Tear down in progress",
        )
    app = AppDeployment.get_latest_version(project_id=project.id, app_id=app_id)
    if app is None:
        return HTTPException(
            status_code=404,
            detail=f"App {app_id} not found",
        )
    run = WorkflowRun.create(
        project_id=project.id,
        workflow_type=WorkflowType.DEPLOY,
        app_id=app_id,
        initiated_by=user_id,
        notification_email=users_email,
    )

    background_tasks.add_task(execute_deploy_single_workflow, run)

    return Response(
        media_type="application/json",
        status_code=201,
        content=jsons.dumps(WorkflowRunSummary.from_workflow_run(run).dict()),
    )


@router.post("/api/project/workflows/uninstall")
async def uninstall_all_apps(
    request: Request,
    background_tasks: BackgroundTasks,
):
    user_id = await get_user_id(request)
    users_email = await get_email(request)

    run = WorkflowRun.create(
        project_id=user_id,
        workflow_type=WorkflowType.DESTROY,
        initiated_by=user_id,
        notification_email=users_email,
    )

    background_tasks.add_task(execute_destroy_all_workflow, run)

    return Response(
        media_type="application/json",
        status_code=201,
        content=jsons.dumps(WorkflowRunSummary.from_workflow_run(run).dict()),
    )


@router.post("/api/project/apps/{app_id}/workflows/uninstall")
async def uninstall_app(
    request: Request,
    background_tasks: BackgroundTasks,
    app_id: str,
    keep_common: bool = False,
):
    user_id = await get_user_id(request)
    users_email = await get_email(request)
    project = Project.get(user_id)
    destroy_common = False
    run = WorkflowRun.create(
        project_id=project.id,
        workflow_type=WorkflowType.DESTROY,
        app_id=app_id,
        initiated_by=user_id,
        notification_email=users_email,
    )
    if not keep_common:
        installed_apps = set()
        for a in project.apps:
            if a not in [Project.COMMON_APP_NAME, app_id]:
                app = AppDeployment.get_latest_deployed_version(project.id, a)
                if app is not None:
                    installed_apps.add(a)
        logger.info(f"Installed apps: {installed_apps}")
        if len(installed_apps) == 0:
            project.update(actions=[Project.destroy_in_progress.set(True)])
            destroy_common = True

    background_tasks.add_task(execute_destroy_single_workflow, run, destroy_common)

    return Response(
        media_type="application/json",
        status_code=201,
        content=jsons.dumps(WorkflowRunSummary.from_workflow_run(run).dict()),
    )


@router.get(
    "/api/project/apps/{app_id}/workflows/{workflow_type}/runs/{run_number}/jobs/{job_number}/logs"
)
async def stream_app_job_logs(
    request: Request,
    app_id: str,
    workflow_type: str,
    run_number: str,
    job_number: int,
):
    return await stream_deployment_logs(
        request=request,
        workflow_type=workflow_type,
        run_number=run_number,
        job_number=job_number,
        owning_app_id=app_id,
    )


@router.get(
    "/api/project/workflows/{workflow_type}/runs/{run_number}/jobs/{job_number}/logs"
)
async def stream_project_job_logs(
    request: Request,
    workflow_type: str,
    run_number: str,
    job_number: int,
):
    return await stream_deployment_logs(
        request=request,
        workflow_type=workflow_type,
        run_number=run_number,
        job_number=job_number,
    )


async def stream_deployment_logs(
    request: Request,
    workflow_type: str,
    run_number: str,
    job_number: int,
    owning_app_id: Optional[str] = None,
):
    user_id = await get_user_id(request)
    project_id = user_id

    workflow_type = (
        None if workflow_type.lower() == "any" else WorkflowType.from_str(workflow_type)
    )

    if owning_app_id == "any":
        owning_app_id = ""

    if not job_number:
        raise HTTPException(status_code=400, detail="Job number is required")

    if run_number == "latest":
        if owning_app_id == "":
            latest_run = WorkflowRun.get_latest_run(
                project_id=user_id, workflow_type=workflow_type
            )
        else:
            user_app = AppDeployment.get_latest_version(
                project_id=user_id, app_id=owning_app_id
            )
            if user_app is None:
                raise HTTPException(status_code=404, detail="App not found")
            elif len(user_app.deployments) == 0:
                raise HTTPException(status_code=404, detail="No deployments found")

            latest_run = WorkflowRun.get_latest_run(
                project_id=user_id,
                workflow_type=workflow_type,
                app_id=(
                    owning_app_id if owning_app_id != Project.COMMON_APP_NAME else None
                ),
            )
        run_composite_id = latest_run.composite_key()
    else:
        run_range_key = WorkflowRun.compose_range_key(
            workflow_type=workflow_type.value,
            app_id=owning_app_id if owning_app_id != Project.COMMON_APP_NAME else None,
            run_number=int(run_number),
        )
        run_composite_id = f"{project_id}#{run_range_key}"

    try:
        job = WorkflowJob.get(run_composite_id, job_number)
    except WorkflowJob.DoesNotExist:
        raise HTTPException(status_code=404, detail="Job not found")

    deploy_dir = DeploymentDir(user_id, run_composite_id)
    deployment_log = deploy_dir.get_log(job.modified_app_id)

    if request.headers.get("accept") == "text/event-stream":

        async def tail():
            try:
                async for line in deployment_log.tail():
                    if await request.is_disconnected():
                        logger.debug("Request disconnected")
                        break
                    yield {
                        "event": "log-line",
                        "data": line,
                        "id": str(uuid.uuid4()),
                    }
                logger.debug("sending done")
                yield {
                    "event": "done",
                    "data": "done",
                    "id": str(uuid.uuid4()),
                }
            except Exception as e:
                logger.error("Error streaming logs", exc_info=e)
                raise
            finally:
                deployment_log.close()

        return EventSourceResponse(tail())

    return StreamingResponse(
        deployment_log.tail(),
        media_type="text/plain",
        headers={"Cache-Control": "no-buffer"},
    )


@router.get("/api/project/workflows/{workflow_type}/runs/{run_number}")
async def get_project_workflow_run(
    request: Request,
    workflow_type: str,
    run_number: str,
):
    user_id = await get_user_id(request)
    project_id = user_id

    workflow_type = (
        None if workflow_type.lower() == "any" else WorkflowType.from_str(workflow_type)
    )

    if run_number == "latest":
        run = WorkflowRun.get_latest_run(
            project_id=project_id, workflow_type=workflow_type
        )
    else:
        run = WorkflowRun.get(
            project_id,
            WorkflowRun.compose_range_key(
                workflow_type=workflow_type.value,
                app_id=None,
                run_number=int(run_number),
            ),
        )

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return WorkflowRunView.from_workflow_run(run)


@router.get("/api/project/apps/{app_id}/workflows/{workflow_type}/runs/{run_number}")
async def get_app_workflow_run(
    request: Request,
    app_id: str,
    workflow_type: str,
    run_number: str,
):
    user_id = await get_user_id(request)
    project_id = user_id

    workflow_type = (
        None if workflow_type.lower() == "any" else WorkflowType.from_str(workflow_type)
    )

    if run_number == "latest":
        run = WorkflowRun.get_latest_run(
            project_id=project_id, workflow_type=workflow_type, app_id=app_id
        )
    else:
        run = WorkflowRun.get(
            project_id,
            WorkflowRun.compose_range_key(
                workflow_type=workflow_type.value,
                app_id=app_id,
                run_number=int(run_number),
            ),
        )

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return WorkflowRunView.from_workflow_run(run)


@router.get("/api/project/workflows/{workflow_type}/runs")
async def get_project_workflow_runs(
    request: Request,
    workflow_type: str,
):
    user_id = await get_user_id(request)
    project_id = user_id

    workflow_type = (
        None if workflow_type.lower() == "any" else WorkflowType.from_str(workflow_type)
    )

    runs = WorkflowRun.query(
        project_id,
        range_key_condition=(
            WorkflowRun.range_key.startswith(f"{workflow_type.value}#")
            if workflow_type
            else None
        ),
    )

    return [WorkflowRunSummary.from_workflow_run(run) for run in runs]


@router.get("/api/project/apps/{app_id}/workflows/{workflow_type}/runs")
async def get_app_workflow_runs(
    request: Request,
    app_id: str,
    workflow_type: str,
):
    user_id = await get_user_id(request)
    project_id = user_id

    workflow_type = (
        None if workflow_type.lower() == "any" else WorkflowType.from_str(workflow_type)
    )

    runs = WorkflowRun.query(
        project_id,
        range_key_condition=(
            WorkflowRun.range_key.startswith(f"{workflow_type.value}#{app_id}#")
            if workflow_type
            else None
        ),
    )

    return [
        WorkflowRunSummary.from_workflow_run(run)
        for run in runs
        if run.app_id() == app_id
    ]
