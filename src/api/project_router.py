from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pynamodb.exceptions import DoesNotExist

from src.auth.token import get_user_id
from src.dependencies.injection import get_binary_storage, get_iac_storage
from src.deployer.models.workflow_run import WorkflowRun, WorkflowType
from src.engine_service.binaries.fetcher import Binary
from src.project import ConfigValues, get_stack_packs
from src.project.common_stack import Feature
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
        apps={k: 0 for k in body.configuration.keys()},
        region=body.region,
        assumed_role_arn=body.assumed_role_arn,
        assumed_role_external_id=body.assumed_role_external_id,
        features=[Feature.HEALTH_MONITOR.value] if body.health_monitor_enabled else [],
    )
    iac_storage = get_iac_storage()
    stack_packs = get_stack_packs()
    with TempDir() as tmp_dir:
        common_policy = await project.run_base(
            stack_packs=[sp for k, sp in stack_packs.items()],
            config=body.configuration.get("base", {}),
            iac_storage=iac_storage,
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        policy = await project.run_pack(
            stack_packs=stack_packs,
            config=body.configuration,
            iac_storage=get_iac_storage(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )

    policy.combine(common_policy)
    project.policy = str(policy)
    project.save()

    return StackResponse(stack=project.to_view_model(), policy=policy.__str__())


class UpdateStackRequest(BaseModel):
    configuration: dict[str, ConfigValues] = None
    assumed_role_arn: str = None
    assumed_role_external_id: str = None
    health_monitor_enabled: bool = True
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
            for app in apps.values():
                if app.status and app.status not in ["UNINSTALLED", "NEW"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot change region while project has deployed "
                        "applications",
                    )
        actions.append(Project.region.set(body.region))
    if len(actions) > 0:
        project.update(actions=actions)

    # TODO: Determine if the base stack needs changing (this will only be true when we have samples that arent just ECS + VPC)
    # If this is the case we also need to build in the diff ability of the base stack to ensure that we arent going to delete any imported resources to other stacks
    # right now we arent tracking which resources are imported outside of which are explicitly defined in the template
    if body.configuration or body.health_monitor_enabled:
        configuration: dict[str, ConfigValues] = body.configuration or {}
        if body.health_monitor_enabled:
            logger.info("Enabling health monitor")
            project.features = [Feature.HEALTH_MONITOR.value]
        else:
            project.features = []
        if body.configuration is None:
            for app, version in project.apps.items():
                app_deployment = AppDeployment.get(
                    project.id, AppDeployment.compose_range_key(app, version)
                )
                configuration[app] = app_deployment.get_configurations()
                logger.info(f"Configuration for {app} is {configuration[app]}")
        stack_packs = get_stack_packs()
        with TempDir() as tmp_dir:
            common_policy = await project.run_base(
                stack_packs=list(stack_packs.values()),
                config=configuration.get("base", {}),
                iac_storage=get_iac_storage(),
                binary_storage=get_binary_storage(),
                tmp_dir=tmp_dir,
            )
            policy = await project.run_pack(
                stack_packs=stack_packs,
                config=configuration,
                iac_storage=get_iac_storage(),
                binary_storage=get_binary_storage(),
                tmp_dir=tmp_dir,
            )
        policy.combine(common_policy)
        policy = str(policy)
        project.update(
            actions=[
                Project.apps.set(project.apps),
                Project.features.set(project.features),
                Project.policy.set(policy),
            ]
        )

    return StackResponse(stack=project.to_view_model(), policy=project.policy)


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

    for app, version in project.apps.items():
        if app == Project.COMMON_APP_NAME:
            continue
        user_app = AppDeployment.get(
            project.id, AppDeployment.compose_range_key(app_id=app, version=version)
        )
        configuration[app] = user_app.get_configurations()
    with TempDir() as tmp_dir:
        policy = await project.run_pack(
            stack_packs=get_stack_packs(),
            config=configuration,
            iac_storage=get_iac_storage(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        common_policy = await project.run_base(
            stack_packs=list(get_stack_packs().values()),
            config=ConfigValues(),
            iac_storage=get_iac_storage(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        policy.combine(common_policy)
        policy = str(policy)
        project.policy = policy
        project.save()
        return StackResponse(stack=project.to_view_model(), policy=policy)


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
        if app == app_id or app == Project.COMMON_APP_NAME:
            continue
        user_app = AppDeployment.get(
            project.id, AppDeployment.compose_range_key(app_id=app, version=version)
        )
        configuration[app] = user_app.get_configurations()

    with TempDir() as tmp_dir:
        policy = await project.run_pack(
            stack_packs=get_stack_packs(),
            config=configuration,
            iac_storage=get_iac_storage(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        common_policy = await project.run_base(
            stack_packs=list(get_stack_packs().values()),
            config=ConfigValues(),
            iac_storage=get_iac_storage(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        policy.combine(common_policy)
        policy = str(policy)
        project.policy = policy
        project.save()
        return StackResponse(stack=project.to_view_model(), policy=policy)


@router.delete("/api/project/{app_name}")
async def remove_app(
    request: Request,
    app_name: str,
):
    user_id = await get_user_id(request)
    project = Project.get(user_id)
    project.apps.pop(app_name)
    configuration: dict[str, ConfigValues] = {}
    for app, version in project.apps.items():
        if app == app_name:
            continue
        user_app = AppDeployment.get(
            project.id, AppDeployment.compose_range_key(app_id=app, version=version)
        )
        configuration[app] = user_app.get_configurations()

    if len(configuration) == 0 or (
        len(configuration) == 1
        and configuration.get(Project.COMMON_APP_NAME, None) is not None
    ):
        project.apps = {}
        project.save()
        return StackResponse(stack=project.to_view_model())

    with TempDir() as tmp_dir:
        policy = await project.run_pack(
            stack_packs=get_stack_packs(),
            config=configuration,
            iac_storage=get_iac_storage(),
            binary_storage=get_binary_storage(),
            tmp_dir=tmp_dir,
        )
        policy = str(policy)
        project.policy = policy
        project.save()
        return StackResponse(stack=project.to_view_model(), policy=policy)
