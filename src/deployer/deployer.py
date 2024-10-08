import json
import os
import re
from dataclasses import dataclass

import boto3
from fastapi import BackgroundTasks

from src.deployer.deploy import run_full_deploy_workflow
from src.deployer.destroy import run_full_destroy_workflow
from src.deployer.models.util import abort_workflow_run, start_workflow_run
from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.models.workflow_run import WorkflowRun
from src.util.logging import logger


@dataclass
class DeployerInput:
    run: WorkflowRun
    common_job: WorkflowJob
    app_jobs: list[WorkflowJob]


def get_deployer(background_tasks: BackgroundTasks):
    if deploy_arn is None:
        return LocalDeployer(background_tasks)
    return StepFunctionDeployer()


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
    def __init__(self) -> None:
        self.client = boto3.client("stepfunctions")

    def _execution_name(self, input: DeployerInput):
        name = input.run.composite_key()
        name = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
        name = re.sub(r"--+", "-", name)
        if len(name) > 80:
            # just in case, make sure it meets the length criteria
            name = name[:80]
        return name

    def _execution_input(self, input: DeployerInput):
        return {
            "input": {
                "projectId": input.run.project_id,
                "runId": input.run.range_key,
                "jobId": input.run.job_id(),
                "jobNumbers": {
                    "common": str(input.common_job.job_number),
                    "apps": [str(j.job_number) for j in input.app_jobs],
                },
            }
        }

    def install(self, input: DeployerInput):
        name = self._execution_name(input)
        logger.info(f"Starting Install StepFunction execution: {name}")
        try:
            self.client.start_execution(
                stateMachineArn=deploy_arn,
                name=name,
                input=json.dumps(self._execution_input(input)),
            )
        except:
            abort_workflow_run(input.run)
            raise
        else:
            start_workflow_run(input.run)

    def uninstall(self, input: DeployerInput):
        name = self._execution_name(input)
        logger.info(f"Starting Uninstall StepFunction execution: {name}")
        try:
            self.client.start_execution(
                stateMachineArn=destroy_arn,
                name=name,
                input=json.dumps(self._execution_input(input)),
            )
        except:
            abort_workflow_run(input.run)
            raise
        else:
            start_workflow_run(input.run)
