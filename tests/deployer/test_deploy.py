
from unittest.mock import patch
import aiounittest

from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import (
    WorkflowRun,
)
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


class TestDeploy(PynamoTest, aiounittest.AsyncTestCase):
    models = [WorkflowRun, WorkflowJob, Project, AppDeployment]
    
    def setUp(self):
        self.project = Project(
            id="project_id",
            name="project_name",
            owner="owner",
            created_at=0,
            updated_at=0,
        )
        self.app = AppDeployment(
            project_id="project_id",
            app_id="app_id",
            app_name="app_name",
            app_version="app_version",
            app_type="app_type",
            app_status=AppLifecycleStatus.ACTIVE,
            app_created_at=0,
            app_updated_at=0,
        )
        self.workflow_run = WorkflowRun(
            project_id="project_id",
            app_id="app_id",
            workflow_id="workflow_id",
            workflow_number=1,
            run_id="run_id",
            run_number=1,
            status=WorkflowJobStatus.PENDING,
        )
        self.job = WorkflowJob(
            job_id="job_id",
            job_number=1,
            project_id="project_id",
            app_id="app_id",
            workflow_id="workflow_id",
            workflow_number=1,
            modified_app_id="app_id",
            type=WorkflowJobType.DEPLOY,
            status=WorkflowJobStatus.PENDING,
        )
        self.job.save()
        self.workflow_run.save()
        self.app.save()
        self.project.save()
        return super().setUp()
    
    @patch("src.deployer.deployer.deploy")
    @patch("src.deployer.deployer.run_pre_deploy_hooks")
    @patch("src.deployer.deployer.generate_iac")
    @patch("src.deployer.deployer.build_app")
    @patch("src.deployer.deployer.read_live_state")
    async def test_deploy_workflow(
        self,
        mock_read_live_state,
        mock_build_app,
        mock_generate_iac,
        mock_run_pre_deploy_hooks,
        mock_deploy,
    ):
        