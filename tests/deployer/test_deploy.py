import datetime
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

import aiounittest

from src.deployer.deploy import (
    deploy,
    deploy_workflow,
    get_pulumi_config,
    run_pre_deploy_hooks,
)
from src.deployer.models.workflow_job import WorkflowJob, WorkflowJobStatus
from src.deployer.models.workflow_run import WorkflowRun
from src.deployer.pulumi.builder import AppBuilder
from src.deployer.pulumi.deployer import AppDeployer
from src.engine_service.engine_commands.run import RunEngineResult
from src.project import StackPack
from src.project.common_stack import CommonStack
from src.project.live_state import LiveState
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


class TestDeploy(PynamoTest, aiounittest.AsyncTestCase):
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
            modified_app_id="metabase",
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

    @patch("src.deployer.deploy.deploy")
    @patch("src.deployer.deploy.run_pre_deploy_hooks")
    @patch("src.deployer.deploy.generate_iac")
    @patch("src.deployer.deploy.build_app")
    @patch("src.deployer.deploy.read_live_state")
    async def test_deploy_workflow(
        self,
        mock_read_live_state,
        mock_build_app,
        mock_generate_iac,
        mock_run_pre_deploy_hooks,
        mock_deploy,
    ):
        mock_live_state = MagicMock(spec=LiveState)
        mock_read_live_state.return_value = mock_live_state
        run_engine_result = RunEngineResult(
            resources_yaml="resources_yaml",
            topology_yaml="topology_yaml",
            iac_topology="iac_topology",
        )
        mock_build_app.return_value = run_engine_result
        mock_generate_iac.return_value = b"bytes"
        mock_deploy.return_value = (WorkflowJobStatus.SUCCEEDED, "Deployed")

        result = await deploy_workflow(self.job.partition_key, self.job.job_number)

        self.assertEqual(
            result, {"status": WorkflowJobStatus.SUCCEEDED.value, "message": "Deployed"}
        )
        mock_build_app.assert_called_once_with(mock.ANY, mock.ANY, mock_live_state)
        mock_generate_iac.assert_called_once_with(run_engine_result, mock.ANY, mock.ANY)
        mock_run_pre_deploy_hooks.assert_called_once_with(mock.ANY, mock_live_state)
        mock_deploy.assert_called_once()

        update_job = WorkflowJob.get(self.job.partition_key, self.job.job_number)
        self.assertEqual(update_job.status, WorkflowJobStatus.SUCCEEDED.value)
        self.assertEqual(update_job.status_reason, "Deployed")
        self.assertIsNotNone(update_job.completed_at)

    @patch("src.deployer.deploy.run_actions")
    async def test_run_pre_deploy_hooks(
        self,
        mock_run_actions,
    ):
        mock_live_state = MagicMock(spec=LiveState)

        run_pre_deploy_hooks(self.job, mock_live_state)

        mock_run_actions.assert_called_once_with(
            self.app, self.project, mock_live_state
        )

    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.get_stack_pack_by_job")
    async def test_get_pulumi_config(
        self,
        mock_get_stack_pack_by_job,
        mock_common_stack,
    ):
        mock_stack_pack = MagicMock(
            spec=StackPack,
            id="sp",
            get_pulumi_configs=MagicMock(return_value={"key": "value"}),
        )
        common_stack = MagicMock(
            spec=CommonStack,
            get_pulumi_configs=MagicMock(return_value={"key2": "value2"}),
        )
        mock_get_stack_pack_by_job.return_value = mock_stack_pack
        mock_common_stack.COMMON_APP_NAME = "common"
        mock_common_stack.return_value = common_stack

        result = get_pulumi_config(self.job)

        self.assertEqual(result, {"key": "value", "key2": "value2"})
        mock_get_stack_pack_by_job.assert_called_once_with(self.job)
        mock_stack_pack.get_pulumi_configs.assert_called_once_with(
            self.app.get_configurations()
        )
        mock_common_stack.assert_called_once_with([mock_stack_pack], [])
        common_stack.get_pulumi_configs.assert_called_once_with(
            self.app.get_configurations()
        )

    @patch("src.deployer.deploy.AppDeployer")
    @patch("src.deployer.deploy.AppBuilder")
    @patch("src.deployer.deploy.get_pulumi_config")
    async def test_deploy(
        self,
        mock_get_pulumi_config,
        mock_app_builder,
        mock_app_deployer,
    ):
        mock_stack = MagicMock(
            set_config=MagicMock(),
        )
        app_builder = MagicMock(
            spec=AppBuilder,
            prepare_stack=MagicMock(return_value=mock_stack),
            configure_aws=MagicMock(),
        )
        app_deployer = MagicMock(
            spec=AppDeployer,
            deploy=MagicMock(return_value=(WorkflowJobStatus.SUCCEEDED, "Deployed")),
        )
        mock_get_pulumi_config.return_value = {"key": "value"}
        mock_app_builder.return_value = app_builder
        mock_app_deployer.return_value = app_deployer

        result = deploy(self.job, Path("/tmp"))

        self.assertEqual(result, (WorkflowJobStatus.SUCCEEDED, "Deployed"))
        mock_get_pulumi_config.assert_called_once_with(self.job)
        app_builder.prepare_stack.assert_called_once_with(self.job)
        app_builder.configure_aws.assert_called_once_with(
            mock_stack,
            self.project.region,
            self.project.assumed_role_arn,
            self.project.assumed_role_external_id,
        )
        mock_stack.set_config.assert_called_once_with("key", mock.ANY)
        app_deployer.deploy.assert_called_once()
