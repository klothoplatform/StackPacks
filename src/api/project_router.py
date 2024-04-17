from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from pynamodb.exceptions import DoesNotExist

from src.auth.token import get_user_id
from src.dependencies.injection import get_binary_storage
from src.deployer.models.workflow_run import WorkflowRun, WorkflowType
from src.engine_service.binaries.fetcher import Binary
from src.project import ConfigValues, get_stack_packs
from src.project.common_stack import Feature
from src.project.cost import CostElement, calculate_costs
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project, ProjectView
from src.util.logging import logger
from src.util.tmp import TempDir

router = APIRouter()


class StackRequest(BaseModel):
    configuration: dict[str, ConfigValues]
    assumed_role_arn: str = None
    assumed_role_external_id: str = None
    health_monitor_enabled: bool = True
    region: str = None


class StackResponse(BaseModel):
    stack: ProjectView
    policy: Optional[str] = None


@router.post("/api/project")
async def create_stack(
    request: Request,
    body: StackRequest,
) -> StackResponse:
    user_id = await get_user_id(request)
    try:
        binary_storage = get_binary_storage()
        binary_storage.ensure_binary(Binary.ENGINE)
        pack = Project.get(user_id)
        if pack is not None:
            raise HTTPException(
                status_code=400,
                detail="Stack already exists for this user, use PATCH to update",
            )
    except DoesNotExist as e:
        logger.debug(f"Project not found for user {user_id}")

    project = Project(
        id=user_id,
        owner=user_id,
        created_by=user_id,
        apps={},
        region=body.region,
        assumed_role_arn=body.assumed_role_arn,
        assumed_role_external_id=body.assumed_role_external_id,
        features=[Feature.HEALTH_MONITOR.value] if body.health_monitor_enabled else [],
    )
    stack_packs = get_stack_packs()
    with TempDir() as tmp_dir:
        project_stack_packs = {
            k: sp for k, sp in stack_packs.items() if k in body.configuration
        }
        await project.run_common_pack(
            stack_packs=[*project_stack_packs.values()],
            config=body.configuration.get("common", {}),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        await project.run_packs(
            stack_packs=project_stack_packs,
            config=body.configuration,
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )

    return StackResponse(
        stack=project.to_view_model(), policy=str(project.get_policy())
    )


class UpdateStackRequest(BaseModel):
    configuration: dict[str, ConfigValues] = None
    assumed_role_arn: str = None
    assumed_role_external_id: str = None
    health_monitor_enabled: bool = None
    region: str = None


@router.patch("/api/project")
async def update_stack(
    request: Request,
    body: UpdateStackRequest,
) -> StackResponse:
    user_id = await get_user_id(request)
    project = Project.get(user_id)
    actions = []

    if body.assumed_role_arn:
        actions.append(Project.assumed_role_arn.set(body.assumed_role_arn))
    if body.assumed_role_external_id:
        actions.append(
            Project.assumed_role_external_id.set(body.assumed_role_external_id)
        )
    if body.region:
        apps = project.to_view_model().stack_packs
        if project.region not in {None, body.region}:
            # check if any apps are deployed to avoid changing region while stack is running
            for app_id in apps.values():
                if app_id.status and app_id.status not in ["UNINSTALLED", "NEW"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot change region while project has deployed "
                        "applications",
                    )
        actions.append(Project.region.set(body.region))
    if len(actions) > 0:
        project.update(actions=actions)

    # TODO: Determine if the common stack needs changing (this will only be true when we have samples that arent just ECS + VPC)
    # If this is the case we also need to build in the diff ability of the base stack to ensure that we arent going to delete any imported resources to other stacks
    # right now we arent tracking which resources are imported outside of which are explicitly defined in the template
    if body.configuration or body.health_monitor_enabled:
        configuration: dict[str, ConfigValues] = body.configuration or {}
        if body.health_monitor_enabled:
            logger.info("Enabling health monitor")
            project.features = [Feature.HEALTH_MONITOR.value]
        elif body.health_monitor_enabled is False:
            project.features = []

        stack_packs = get_stack_packs()
        initial_apps = {**project.apps}
        for app_deployment in project.get_app_deployments():
            app_id = app_deployment.app_id()
            configuration[app_id] = ConfigValues(
                {
                    **app_deployment.get_configurations(),
                    **configuration.get(app_id, {}),
                }
            )
        with TempDir() as tmp_dir:
            await project.run_base(
                stack_packs=[
                    stack_packs[a] for a in configuration.keys() if a in stack_packs
                ],
                config=configuration.get("base", {}),
                binary_storage=get_binary_storage(),
                tmp_dir=tmp_dir,
            )
            await project.run_pack(
                stack_packs=stack_packs,
                config=configuration,
                binary_storage=get_binary_storage(),
                tmp_dir=tmp_dir,
            )

            current_apps = [*project.apps.keys()]
            project_stack_packs = []
            if current_apps != [*initial_apps.keys()]:
                for app_id in current_apps:
                    if app_id in stack_packs:
                        project_stack_packs.append(stack_packs[app_id])

            await project.run_common_pack(
                stack_packs=project_stack_packs,
                config=configuration.get("common", {}),
                binary_storage=get_binary_storage(),
                tmp_dir=tmp_dir,
            )

    return StackResponse(
        stack=project.to_view_model(), policy=str(project.get_policy())
    )


@router.get("/api/project")
async def my_stack(request: Request) -> ProjectView:
    user_id = await get_user_id(request)
    try:
        project = Project.get(user_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Stack not found")
    return project.to_view_model()


@router.get("/api/project/workflows/runs")
async def get_workflow_runs(
    request: Request,
):
    user_id = await get_user_id(request)

    workflow_type = request.query_params.get("type")
    if workflow_type:
        try:
            workflow_type = WorkflowType.from_str(workflow_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workflow type")

    return list(
        WorkflowRun.query(
            user_id,
            filter_condition=(
                WorkflowRun.type == workflow_type if workflow_type else None
            ),
        )
    )


class AppRequest(BaseModel):
    configuration: ConfigValues


@router.post("/api/project/{app_id}")
async def add_app(
    request: Request,
    app_id: str,
    body: AppRequest,
) -> StackResponse:
    user_id = await get_user_id(request)
    project = Project.get(user_id)
    configuration: dict[str, ConfigValues] = {app_id: body.configuration}

    if project.apps.get(app_id, None) is not None:
        raise HTTPException(
            status_code=400,
            detail="App already exists in stack, use PATCH to update",
        )

    for user_app in project.get_app_deployments():
        configuration[user_app.app_id()] = user_app.get_configurations()

    with TempDir() as tmp_dir:
        stack_packs = get_stack_packs()
        await project.run_packs(
            stack_packs=stack_packs,
            config=configuration,
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        common_policy = await project.run_common_pack(
            stack_packs=[
                stack_packs[a] for a in configuration.keys() if a in stack_packs
            ],
            config=ConfigValues(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        return StackResponse(
            stack=project.to_view_model(), policy=str(project.get_policy())
        )


@router.patch("/api/project/{app_id}")
async def update_app(
    request: Request,
    app_id: str,
    body: AppRequest,
) -> StackResponse:
    user_id = await get_user_id(request)
    project = Project.get(user_id)
    configuration: dict[str, ConfigValues] = {app_id: body.configuration}
    for app, version in project.apps.items():
        if app == Project.COMMON_APP_NAME:
            continue
        user_app = AppDeployment.get(
            project.id, AppDeployment.compose_range_key(app_id=app, version=version)
        )
        if app == app_id:
            # merge user-supplied configuration with existing configuration (shallow merge)
            configuration[app] = ConfigValues(
                {**user_app.get_configurations(), **body.configuration}
            )
        else:
            configuration[app] = user_app.get_configurations()

    with TempDir() as tmp_dir:
        await project.run_packs(
            stack_packs=get_stack_packs(),
            config=configuration,
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        await project.run_common_pack(
            stack_packs=list(get_stack_packs().values()),
            config=ConfigValues(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        return StackResponse(
            stack=project.to_view_model(), policy=str(project.get_policy())
        )


@router.delete("/api/project/{app_name}")
async def remove_app(
    request: Request,
    app_name: str,
):
    user_id = await get_user_id(request)
    project = Project.get(user_id)
    project.apps.pop(app_name)
    configuration: dict[str, ConfigValues] = {}
    common_app_config: ConfigValues = {}
    sps = get_stack_packs()
    project_stack_packs = {}
    for app in project.get_app_deployments():
        app_id = app.app_id()
        if app_id == Project.COMMON_APP_NAME:
            common_app_config = app.get_configurations()
            continue
        configuration[app_id] = app.get_configurations()
        if app_id in sps and app_id != app_name:
            project_stack_packs[app_id] = sps[app_id]

    if len(configuration) == 0 or (
        len(configuration) == 1
        and configuration.get(Project.COMMON_APP_NAME, None) is not None
    ):
        project.apps = {}
        project.save()
        return StackResponse(stack=project.to_view_model())

    with TempDir() as tmp_dir:
        await project.run_packs(
            stack_packs=project_stack_packs,
            config=configuration,
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )

        common_config_fields = {*project.common_stackpack().configuration.keys()}
        await project.run_common_pack(
            stack_packs=list(get_stack_packs().values()),
            config=ConfigValues(
                {
                    k: v
                    for k, v in common_app_config.items()
                    if k in common_config_fields
                }
            ),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        return StackResponse(
            stack=project.to_view_model(), policy=str(project.get_policy())
        )


class CostRequest(BaseModel):
    operation: Optional[str] = Field(default=None)
    app_ids: Optional[list[str]] = Field(default=None)


class CostResponse(BaseModel):
    current: list[CostElement]
    pending: Optional[list[CostElement]] = Field(default=None)


@router.post("/api/cost")
async def get_costs(
    request: Request,
    body: CostRequest,
):
    user_id = await get_user_id(request)
    project = Project.get(user_id)

    current_apps = [
        a
        for a in project.apps
        if AppDeployment.get_latest_deployed_version(project.id, a) is not None
    ]
    current_cost = calculate_costs(project, "install", current_apps)
    if body.operation is not None:
        if body.app_ids is None:
            current_cost.close()
            raise HTTPException(
                status_code=400,
                detail="App IDs must be provided when operation is specified",
            )

        pending_cost = calculate_costs(project, body.operation, body.app_ids)

        return CostResponse(
            current=await current_cost,
            pending=await pending_cost,
        )

    return CostResponse(current=await current_cost, pending=None)
