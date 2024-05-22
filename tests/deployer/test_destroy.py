import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import aiounittest

from src.deployer.deploy import WorkflowResult
from src.deployer.destroy import can_destroy, destroy, destroy_workflow
from src.deployer.models.workflow_job import WorkflowJob, WorkflowJobStatus
from src.deployer.models.workflow_run import WorkflowRun
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deployer import AppDeployer
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


class TestDestroy(PynamoTest, aiounittest.AsyncTestCase):
    models = [WorkflowRun, WorkflowJob, Project, AppDeployment]

    def setUp(self):
        super().setUp()
        t = datetime.datetime.now(datetime.timezone.utc)
        self.project = Project(
            owner="google-oauth2",
            assumed_role_external_id="a696fb6e-75a2-47a8-ba4d-1a89e1aa2e0e",
            destroy_in_progress=False,
            features=["health_monitor"],
            assumed_role_arn="arn:aws:iam:::role/TestRole",
            id="project_id",
            region="us-east-1",
            created_by="google-oauth2",
            created_at=t,
            apps={"common": 1, "metabase": 1},
        )
        self.app = AppDeployment(
            configuration={},
            project_id="project_id",
            range_key="metabase#00000001",
            created_by="google-oauth2",
            created_at=t,
            deployments=["user#DEPLOY##00000001#2"],
        )
        self.common_app = AppDeployment(
            configuration={},
            project_id="project_id",
            range_key="common#00000001",
            created_by="google-oauth2",
            created_at=t,
        )
        self.workflow_run = WorkflowRun(
            initiated_by="google-oauth2",
            notification_email="@klo.dev",
            project_id="project_id",
            range_key="DEPLOY##1",
            status_reason="Workflow run in progress",
            type="DEPLOY",
            created_at=t,
            status="IN_PROGRESS",
        )
        self.job = WorkflowJob(
            initiated_by="google-oauth2",
            job_type="DESTROY",
            partition_key="project_id#DEPLOY#metabase#00000001",
            modified_app="metabase#00000001",
            job_number=1,
            status_reason="Stack removed successfully.",
            title="DEPLOY Metabase",
            dependencies=[],
            status="FAILED",
            created_at=t,
        )
        self.workflow_run.save()
        self.app.save()
        self.common_app.save()
        self.project.save()
        self.job.save()
        return

    @patch("src.deployer.destroy.destroy")
    async def test_destroy_workflow(
        self,
        mock_destroy,
    ):
        mock_destroy.return_value = (WorkflowJobStatus.SUCCEEDED, "Destroyed")

        result = await destroy_workflow(self.job.partition_key, self.job.job_number)

        self.assertEqual(
            result,
            WorkflowResult(status=WorkflowJobStatus.SUCCEEDED, message="Destroyed"),
        )

        mock_destroy.assert_called_once()
        update_job = WorkflowJob.get(self.job.partition_key, self.job.job_number)
        self.assertEqual(update_job.status, WorkflowJobStatus.SUCCEEDED.value)
        self.assertEqual(update_job.status_reason, "Destroyed")
        self.assertIsNotNone(update_job.completed_at)

    @patch.object(AppDeployment, "get_status")
    async def test_can_destroy(
        self,
        mock_get_status,
    ):
        self.assertTrue(can_destroy(self.project.id, self.app.app_id()))

        mock_get_status.return_value = (
            AppDeployment(),
            AppLifecycleStatus.UNINSTALLED,
            "UNINSTALLED",
        )
        self.assertTrue(can_destroy(self.project.id, self.common_app.app_id()))
        mock_get_status.assert_called_once_with(
            self.project.id, self.common_app.app_id()
        )
        mock_get_status.reset_mock()

        mock_get_status.return_value = (
            AppDeployment(),
            AppLifecycleStatus.INSTALLED,
            "INSTALLED",
        )
        self.assertFalse(can_destroy(self.project.id, self.common_app.app_id()))
        mock_get_status.assert_called_once_with(
            self.project.id, self.common_app.app_id()
        )

    @patch("src.deployer.destroy.AppDeployer")
    @patch("src.deployer.destroy.AppBuilder")
    @patch("src.deployer.destroy.get_iac_storage")
    async def test_destroy(
        self,
        mock_get_iac_storage,
        mock_app_builder,
        mock_app_deployer,
    ):
        mock_stack = MagicMock(
            set_config=MagicMock(),
        )
        app_builder = MagicMock(
            spec=AppBuilder,
            write_iac_to_disk=MagicMock(),
            prepare_stack=MagicMock(return_value=mock_stack),
            configure_aws=MagicMock(),
        )
        app_deployer = MagicMock(
            spec=AppDeployer,
            destroy_and_remove_stack=MagicMock(
                return_value=(WorkflowJobStatus.SUCCEEDED, "Destroyed")
            ),
        )
        iac_storage = MagicMock(get_iac=MagicMock(return_value=b"iac"))
        mock_app_builder.return_value = app_builder
        mock_app_deployer.return_value = app_deployer
        mock_get_iac_storage.return_value = iac_storage
        result = destroy(self.job, Path("/tmp"))

        self.assertEqual(result, (WorkflowJobStatus.SUCCEEDED, "Destroyed"))
        app_builder.prepare_stack.assert_called_once_with(self.job)
        app_builder.configure_aws.assert_called_once_with(
            mock_stack,
            self.project.region,
            self.project.assumed_role_arn,
            self.project.assumed_role_external_id,
        )
        app_deployer.destroy_and_remove_stack.assert_called_once()
        iac_storage.get_iac.assert_called_once_with(
            self.project.id, self.app.app_id(), self.app.version()
        )
        app_builder.write_iac_to_disk.assert_called_once_with(b"iac")
