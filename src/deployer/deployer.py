import json
import os
from dataclasses import dataclass

import boto3
from fastapi import BackgroundTasks

from src.deployer.deploy import run_full_deploy_workflow
from src.deployer.destroy import run_full_destroy_workflow
from src.deployer.models.util import start_workflow_run
from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.models.workflow_run import WorkflowRun


@dataclass
class DeployerInput:
    run: WorkflowRun
    common_job: WorkflowJob
    app_jobs: list[WorkflowJob]


def get_deployer(background_tasks: BackgroundTasks):
    if deploy_arn is None:
        return LocalDeployer(background_tasks)
    return StepFunctionDeployer(background_tasks)


class LocalDeployer:
    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    def install(self, input: DeployerInput):
        self.background_tasks.add_task(
            run_full_deploy_workflow, input.run, input.common_job
        )

    def uninstall(self, input: DeployerInput):
        self.background_tasks.add_task(
            run_full_destroy_workflow, input.run, input.common_job
        )


deploy_arn = os.environ.get("DEPLOY_STEP_FUNCTION_ARN", None)
destroy_arn = os.environ.get("DESTROY_STEP_FUNCTION_ARN", None)


class StepFunctionDeployer:
    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self.client = boto3.client("stepfunctions")
        self.background_tasks = background_tasks

    def install(self, input: DeployerInput):
        name = input.run.composite_key()
        name.replace(r"[^a-zA-Z0-9_-]", "-").replace(r"--+", "-")
        self.client.start_execution(
            stateMachineArn=deploy_arn,
            name=name,
            input=json.dumps(
                {
                    "projectId": input.run.project_id,
                    "runId": input.run.run_id(),
                    "jobIds": {
                        "common": input.common_job.job_number,
                        "apps": [j.job_number for j in input.app_jobs],
                    },
                }
            ),
        )
        start_workflow_run(input.run)

    def uninstall(self, input: DeployerInput):
        # TODO - switch to destroy_arn when implemented
        self.background_tasks.add_task(
            run_full_destroy_workflow, input.run, input.common_job
        )
