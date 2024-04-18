# Path: src/api/state_machine.py
# Compare this snippet from src/deployer/pulumi/manager.py:

from io import BytesIO
from pathlib import Path

from pulumi import automation as auto

from src.dependencies.injection import (
    get_binary_storage,
    get_iac_storage,
    get_pulumi_state_bucket_name,
)
from src.deployer.models.pulumi_stack import PulumiStack
from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.manager import AppManager
from src.engine_service.binaries.fetcher import Binary
from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import RunEngineResult
from src.project import get_stack_packs
from src.project.common_stack import CommonStack
from src.project.live_state import LiveState
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from src.util.compress import zip_directory_recurse
from src.util.logging import logger
from src.util.tmp import TempDir


async def read_live_state(project_id: str, app_id: str) -> LiveState:
    common_app = AppDeployment.get_latest_deployed_version(project_id, app_id)
    hash_key, range_key = PulumiStack.split_composite_key(
        common_app.iac_stack_composite_key
    )
    pulumi_stack = PulumiStack.get(hash_key, range_key)
    stack: auto.Stack = AppBuilder.select_stack(
        pulumi_stack, get_pulumi_state_bucket_name()
    )
    manager = AppManager(stack)
    with TempDir() as tmp_dir:
        live_state = await manager.read_deployed_state(tmp_dir)
        return live_state


def get_constraints_from_common_live_state(
    project: Project, live_state: LiveState
) -> list:
    if live_state is None:
        return []
    stack_packs = get_stack_packs()
    common_version = project.apps.get(Project.COMMON_APP_NAME, 0)
    if common_version == 0:
        raise ValueError("Common stack not found")

    common_app = AppDeployment.get(
        project.id,
        AppDeployment.compose_range_key(
            app_id=Project.COMMON_APP_NAME, version=common_version
        ),
    )
    common_stack = CommonStack(list(stack_packs.values()), project.features)
    return live_state.to_constraints(common_stack, common_app.configuration)


async def build_app(
    deployment_job: WorkflowJob, tmp_dir: Path, live_state: LiveState = None
) -> RunEngineResult:
    job_composite_key = deployment_job.composite_key()
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    binary_storage = get_binary_storage()
    project, app = deployment_job.get_project_and_app()
    stack_pack = deployment_job.get_stack_pack()
    logger.info(f"Running {project_id}/{app_id}, deployment id {job_composite_key}")
    engine_result = await app.run_app(
        stack_pack=stack_pack,
        app_dir=tmp_dir,
        binary_storage=binary_storage,
        imports=get_constraints_from_common_live_state(project, live_state),
    )
    return engine_result


async def generate_iac(
    run_result: RunEngineResult, deployment_job: WorkflowJob, tmp_dir: Path
):
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id
    _, app = deployment_job.get_project_and_app()
    binary_storage = get_binary_storage()
    iac_storage = get_iac_storage()
    binary_storage.ensure_binary(Binary.IAC)
    await export_iac(
        ExportIacRequest(
            input_graph=run_result.resources_yaml,
            name=app_id,
            tmp_dir=tmp_dir,
        )
    )
    stack_pack = deployment_job.get_stack_pack()
    stack_pack.copy_files(app.get_configurations(), tmp_dir)
    iac_bytes = zip_directory_recurse(BytesIO(), tmp_dir)
    logger.info(f"Writing IAC for {app_id} version {app.version()}")
    iac_storage.write_iac(project_id, app_id, app.version(), iac_bytes)
    return
