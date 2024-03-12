from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pynamodb.exceptions import DoesNotExist

from src.auth.token import get_user_id
from src.dependencies.injection import get_iac_storage
from src.stack_pack import ConfigValues, StackConfig, get_stack_packs
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack, UserStack
from src.util.aws.iam import Policy
from src.util.logging import logger
from src.util.tmp import TempDir

router = APIRouter()


class StackRequest(BaseModel):
    configuration: dict[str, ConfigValues]
    assumed_role_arn: str = None
    region: str = None


class StackResponse(BaseModel):
    stack: UserStack
    policy: Optional[str] = None


@router.post("/api/stack")
async def create_stack(
    request: Request,
    body: StackRequest,
) -> StackResponse:
    policy: Policy = None
    user_id = await get_user_id(request)
    try:
        pack = UserPack.get(user_id)
        if pack is not None:
            raise HTTPException(
                status_code=400,
                detail="Stack already exists for this user, use PATCH to update",
            )
    except DoesNotExist as e:
        logger.debug(f"UserPack not found for user {user_id}")

    user_pack = UserPack(
        id=user_id,
        owner=user_id,
        created_by=user_id,
        apps={k: 0 for k in body.configuration.keys()},
        region=body.region,
        assumed_role_arn=body.assumed_role_arn,
    )
    stack_packs = get_stack_packs()
    policy: Policy = None
    common_policy: Policy = None
    iac_storage = get_iac_storage()
    stack_packs = get_stack_packs()
    with TempDir() as tmp_dir:
        common_policy = await user_pack.run_base(
            [sp for k, sp in stack_packs.items()],
            body.configuration.get("base", {}),
            iac_storage,
            tmp_dir,
        )
        policy = await user_pack.run_pack(stack_packs, body.configuration, tmp_dir)
    user_pack.save()
    policy.combine(common_policy)
    return StackResponse(stack=user_pack.to_user_stack(), policy=policy.__str__())


class UpdateStackRequest(BaseModel):
    configuration: dict[str, ConfigValues] = None
    assumed_role_arn: str = None
    region: str = None


@router.patch("/api/stack")
async def update_stack(
    request: Request,
    body: UpdateStackRequest,
) -> StackResponse:
    policy: Policy = None
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id)
    actions = []
    if body.assumed_role_arn:
        actions.append(UserPack.assumed_role_arn.set(body.assumed_role_arn))
    if body.region:
        # TODO: add check to see if they have already deployed a stack and its running, if so send back a 400 since we cant change region
        actions.append(UserPack.region.set(body.region))
    if len(actions) > 0:
        user_pack.update(actions=actions)

    # TODO: Determine if the base stack needs changing (this will only be true when we have samples that arent just ECS + VPC)
    # If this is the case we also need to build in the diff ability of the base stack to ensure that we arent going to delete any imported resources to other stacks
    # right now we arent tracking which resources are imported outside of which are explicitly defined in the template
    if body.configuration:
        stack_packs = get_stack_packs()
        with TempDir() as tmp_dir:
            common_policy = await user_pack.run_base(
                stack_packs.values(),
                body.configuration.get("base", {}),
                get_iac_storage(),
                tmp_dir,
            )
            policy = await user_pack.run_pack(stack_packs, body.configuration, tmp_dir)
        policy.combine(common_policy)
        user_pack.update(actions=[UserPack.apps.set(user_pack.apps)])

    return StackResponse(stack=user_pack.to_user_stack(), policy=policy.__str__())


@router.get("/api/stack")
async def my_stack(request: Request) -> UserStack:
    user_id = await get_user_id(request)
    try:
        user_pack = UserPack.get(user_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Stack not found")
    return user_pack.to_user_stack()


@router.get("/api/stackpacks")
async def list_stackpacks():
    sps = get_stack_packs()

    def config_to_dict(cfg: StackConfig):
        c = {
            "name": cfg.name,
            "description": cfg.description,
            "type": cfg.type,
            "secret": cfg.secret,
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
            "id": spid,
            "name": sp.name,
            "version": sp.version,
            "configuration": {
                k: config_to_dict(cfg) for k, cfg in sp.configuration.items()
            },
        }
        for spid, sp in sps.items()
        if not spid.startswith("test_")
    }


class AppRequest(BaseModel):
    configuration: ConfigValues


@router.post("/api/stack/{app_name}")
async def add_app(
    request: Request,
    app_name: str,
    body: AppRequest,
) -> StackResponse:
    policy: Policy = None
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id)
    configuration: dict[str, ConfigValues] = {app_name: body.configuration}

    if user_pack.apps.get(app_name, None) is not None:
        return HTTPException(
            status_code=400,
            detail="App already exists in stack, use PATCH to update",
        )

    for app, version in user_pack.apps.items():
        if app == UserPack.COMMON_APP_NAME:
            continue
        user_app = UserApp.get(UserApp.composite_key(user_pack.id, app), version)
        configuration[app] = user_app.get_configurations()
    with TempDir() as tmp_dir:
        policy = await user_pack.run_pack(get_stack_packs(), configuration, tmp_dir)
        common_policy = await user_pack.run_base(
            list(get_stack_packs().values()), {}, get_iac_storage(), tmp_dir
        )
        policy.combine(common_policy)
        user_pack.save()
        return StackResponse(stack=user_pack.to_user_stack(), policy=str(policy))


@router.patch("/api/stack/{app_name}")
async def update_app(
    request: Request,
    app_name: str,
    body: AppRequest,
) -> StackResponse:
    policy: Policy = None
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id)
    configuration: dict[str, ConfigValues] = {app_name: body.configuration}
    for app, version in user_pack.apps.items():
        if app == app_name or app == UserPack.COMMON_APP_NAME:
            continue
        user_app = UserApp.get(UserApp.composite_key(user_pack.id, app), version)
        configuration[app] = user_app.get_configurations()

    with TempDir() as tmp_dir:
        policy = await user_pack.run_pack(get_stack_packs(), configuration, tmp_dir)
        common_policy = await user_pack.run_base(
            list(get_stack_packs().values()), {}, get_iac_storage(), tmp_dir
        )
        policy.combine(common_policy)
        user_pack.save()
        return StackResponse(stack=user_pack.to_user_stack(), policy=policy.__str__())


@router.delete("/api/stack/{app_name}")
async def remove_app(
    request: Request,
    app_name: str,
):
    policy: Policy = None
    user_id = await get_user_id(request)
    user_pack = UserPack.get(user_id)
    user_pack.apps.pop(app_name)
    configuration: dict[str, ConfigValues] = {}
    for app, version in user_pack.apps.items():
        if app == app_name:
            continue
        user_app = UserApp.get(UserApp.composite_key(user_pack.id, app), version)
        configuration[app] = user_app.get_configurations()

    if len(configuration) == 0 or (
        len(configuration) == 1
        and configuration.get(UserPack.COMMON_APP_NAME, None) is not None
    ):
        user_pack.apps = {}
        user_pack.save()
        return StackResponse(stack=user_pack.to_user_stack())

    with TempDir() as tmp_dir:
        policy = await user_pack.run_pack(get_stack_packs(), configuration, tmp_dir)
        user_pack.save()
        return StackResponse(stack=user_pack.to_user_stack(), policy=str(policy))
