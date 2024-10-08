import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from aiomultiprocess import Pool
from pulumi import automation as auto

from src.dependencies.injection import get_pulumi_state_bucket_name
from src.deployer.engine import build_app, generate_iac, read_live_state
from src.deployer.models.util import (
    abort_workflow_run,
    complete_workflow_run,
    start_workflow_run,
)
from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import WorkflowRun
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.deployer.pulumi.deployer import AppDeployer
from src.deployer.pulumi.manager import AppManager
from src.deployer.util import (
    get_app_workflows,
    get_expected_outputs_for_job,
    get_project_and_app,
    get_stack_pack_by_job,
    send_email,
)
from src.project.actions import run_actions
from src.project.common_stack import CommonStack
from src.project.live_state import LiveState
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from src.util.logging import MetricNames, MetricsLogger, logger
from src.util.tmp import TempDir


@dataclass
class WorkflowResult:
    status: WorkflowJobStatus
    message: str

    def __str__(self):
        return json.dumps(self.__dict__)


async def deploy_workflow(job_id: str, job_number: int):
    workflow_job = WorkflowJob.get(job_id, job_number)
    metrics_logger = MetricsLogger(
        workflow_job.project_id(), workflow_job.modified_app_id()
    )
    project, app = get_project_and_app(workflow_job)
    logger.info(
        f"Deploying {project.id}/{app.app_id()} for deployment job {job_id}/{job_number}"
    )
    try:
        workflow_job.update(
            actions=[WorkflowJob.status.set(WorkflowJobStatus.IN_PROGRESS.value)]
        )
        live_state = None
        if workflow_job.modified_app_id() != CommonStack.COMMON_APP_NAME:
            live_state = await read_live_state(
                workflow_job.project_id(), CommonStack.COMMON_APP_NAME
            )
        with TempDir() as tmp_dir:
            if workflow_job.modified_app_id() != CommonStack.COMMON_APP_NAME:
                # We need to run the pre deploy hooks before building the app in case the outputs are used as config
                success = run_pre_deploy_hooks(workflow_job, live_state)
                if not success:
                    raise ValueError("Error running pre-deploy hooks")
            run_engine_result = await build_app(workflow_job, tmp_dir, live_state)
            await generate_iac(run_engine_result, workflow_job, tmp_dir)
            manager, deploy_status, deploy_message = deploy(workflow_job, tmp_dir)
            outputs = get_expected_outputs_for_job(workflow_job)
            stack_outputs = manager.get_outputs(outputs)
            metrics_logger.log_metric(
                MetricNames.PULUMI_DEPLOYMENT_FAILURE,
                1 if deploy_status == WorkflowJobStatus.FAILED else 0,
            )
            app.update(
                actions=[
                    AppDeployment.outputs.set(stack_outputs),
                ],
            )
            workflow_job.update(
                actions=[
                    WorkflowJob.status.set(deploy_status.value),
                    WorkflowJob.status_reason.set(deploy_message),
                    WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
                ]
            )
            metrics_logger.log_metric(
                MetricNames.DEPLOYMENT_WORKFLOW_FAILURE,
                0,
            )
            return WorkflowResult(deploy_status, deploy_message)
    except Exception as e:
        metrics_logger.log_metric(
            MetricNames.DEPLOYMENT_WORKFLOW_FAILURE,
            1,
        )
        logger.error(
            f"Error deploying {workflow_job.composite_key()}: {e}", exc_info=True
        )
        workflow_job.update(
            actions=[
                WorkflowJob.status.set(WorkflowJobStatus.FAILED.value),
                WorkflowJob.status_reason.set(str(e)),
            ]
        )
        return WorkflowResult(WorkflowJobStatus.FAILED, "Internal Error")


def run_pre_deploy_hooks(deployment_job: WorkflowJob, live_state: LiveState):
    logger.info(f"Running pre-deploy hooks for {deployment_job.composite_key()}")
    project, app = get_project_and_app(deployment_job)
    return run_actions(app, project, live_state)


def get_pulumi_config(deployment_job: WorkflowJob) -> dict[str, str]:
    logger.info(f"Getting pulumi config for {deployment_job.composite_key()}")
    stack_pack = get_stack_pack_by_job(deployment_job)
    project, app = get_project_and_app(deployment_job)
    pulumi_config = stack_pack.get_pulumi_configs(app.get_configurations())
    if stack_pack.id != CommonStack.COMMON_APP_NAME:
        common_app = AppDeployment.get(
            project.id,
            AppDeployment.compose_range_key(
                app_id=CommonStack.COMMON_APP_NAME,
                version=project.apps[CommonStack.COMMON_APP_NAME],
            ),
        )
        common_config = CommonStack([stack_pack], []).get_pulumi_configs(
            common_app.get_configurations()
        )
        pulumi_config.update(common_config)
    return pulumi_config


def deploy(
    deployment_job: WorkflowJob, tmp_dir: Path
) -> tuple[AppManager, WorkflowJobStatus, str]:
    logger.info(f"Deploying app for deployment job {deployment_job.composite_key()}")
    project_id = deployment_job.project_id()
    app_id = deployment_job.modified_app_id()
    project, app = get_project_and_app(deployment_job)
    run_id = deployment_job.partition_key
    logger.info(
        f"Building {project_id}/{app_id}, deployment id {deployment_job.composite_key()}"
    )

    pulumi_config = get_pulumi_config(deployment_job)

    builder = AppBuilder(tmp_dir, get_pulumi_state_bucket_name())
    stack = builder.prepare_stack(deployment_job)
    builder.configure_aws(
        stack,
        project.region,
        project.assumed_role_arn,
        project.assumed_role_external_id,
    )
    for k, v in pulumi_config.items():
        stack.set_config(k, auto.ConfigValue(v, secret=True))
    deployer = AppDeployer(
        stack,
        DeploymentDir(project_id, run_id),
    )
    logger.info(
        f"Deploying {project_id}/{app_id}, deployment id {deployment_job.composite_key()}"
    )
    manager = AppManager(stack)
    deploy_result = deployer.deploy()
    return manager, deploy_result[0], deploy_result[1]


def create_deploy_workflow_jobs(
    run: WorkflowRun,
    apps: List[str],
) -> WorkflowJob:
    project_id = run.project_id
    project = Project.get(project_id)

    if project.destroy_in_progress:
        raise ValueError("Pack is currently being torn down")

    job_id = run.job_id()
    deploy_common_job = WorkflowJob.create_job(
        partition_key=job_id,
        job_type=WorkflowJobType.DEPLOY,
        modified_app_id=CommonStack.COMMON_APP_NAME,
        modified_app_version=project.apps[CommonStack.COMMON_APP_NAME],
        initiated_by=run.initiated_by,
    )
    deploy_app_jobs = []
    for app_name in apps:
        if app_name == CommonStack.COMMON_APP_NAME:
            continue
        deploy_app_jobs.append(
            WorkflowJob.create_job(
                partition_key=job_id,
                job_type=WorkflowJobType.DEPLOY,
                modified_app_id=app_name,
                modified_app_version=project.apps[app_name],
                initiated_by=run.initiated_by,
                dependencies=[deploy_common_job.composite_key()],
            )
        )
    return deploy_common_job, deploy_app_jobs


async def run_full_deploy_workflow(run: WorkflowRun, common_job: WorkflowJob):

    try:
        start_workflow_run(run)
        async with Pool() as pool:
            tasks: list[WorkflowResult] = []
            task = pool.apply(
                deploy_workflow,
                kwds=dict(
                    job_id=run.composite_key(),
                    job_number=common_job.job_number,
                ),
            )
            tasks.append(task)
            results: list[WorkflowResult] = await asyncio.gather(*tasks)
            logger.info(f"Tasks: {tasks}")

        if results[0].status != WorkflowJobStatus.SUCCEEDED:
            abort_workflow_run(run)
            return
    except Exception as e:
        logger.error(f"Error deploying {run.composite_key()}: {e}")
        abort_workflow_run(run)
        return

    try:
        app_flows = get_app_workflows(run)
        async with Pool() as pool:
            tasks: list[WorkflowResult] = []
            for app_flow in app_flows:
                task = pool.apply(
                    deploy_workflow,
                    kwds=dict(
                        job_id=app_flow["id"],
                        job_number=app_flow["job_number"],
                    ),
                )
                tasks.append(task)

            results: list[WorkflowResult] = await asyncio.gather(*tasks)
            logger.info(f"Tasks: {tasks}")

        if all(result.status == WorkflowJobStatus.SUCCEEDED for result in results):
            send_email(run)

        complete_workflow_run(run)
    except Exception as e:
        logger.error(f"Error deploying {run.composite_key()}: {e}")
        complete_workflow_run(run)
