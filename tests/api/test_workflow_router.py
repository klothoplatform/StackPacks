import datetime
from unittest.mock import MagicMock, patch

import aiounittest
from sse_starlette import EventSourceResponse

from src.api.models.workflow_models import WorkflowRunSummary
from src.api.workflow_router import (
    install,
    install_app,
    stream_deployment_logs,
    uninstall_all_apps,
    uninstall_app,
)
from src.deployer.deploy import run_full_deploy_workflow
from src.deployer.destroy import run_full_destroy_workflow
from src.deployer.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowType,
)
from src.project import StackPack
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


class TestWorkflowRouter(PynamoTest, aiounittest.AsyncTestCase):
    models = [Project]

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
        self.project.save()
        return

    @patch("src.api.workflow_router.create_deploy_workflow_jobs")
    @patch.object(WorkflowRunSummary, "from_workflow_run")
    @patch("src.api.workflow_router.WorkflowRun")
    @patch("src.api.workflow_router.get_email")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.BackgroundTasks")
    @patch("src.api.workflow_router.uuid")
    async def test_install(
        self,
        mock_uuid,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
        mock_workflow_run,
        mock_from_workflow_run,
        mock_create_deploy_workflow_jobs,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "project_id"
        mock_get_email.return_value = "users_email"

        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DEPLOY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance

        mock_from_workflow_run.return_value = MagicMock(
            model_dump=MagicMock(return_value={"id": "deployment_id"})
        )
        common_job = MagicMock()
        mock_create_deploy_workflow_jobs.return_value = common_job

        sp = MagicMock(spec=StackPack)

        response = await install(
            MagicMock(),
            mock_bg,
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            run_full_deploy_workflow, mock_wf_run_instance, common_job
        )
        mock_create_deploy_workflow_jobs.assert_called_once_with(
            mock_wf_run_instance,
            list(self.project.apps.keys()),
        )
        mock_from_workflow_run.assert_called_once_with(mock_wf_run_instance)

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            b'{"id": "deployment_id"}',
            response.body,
        )

    @patch("src.api.workflow_router.create_deploy_workflow_jobs")
    @patch.object(WorkflowRunSummary, "from_workflow_run")
    @patch("src.api.workflow_router.WorkflowRun")
    @patch("src.api.workflow_router.get_email")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.BackgroundTasks")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_version")
    async def test_install_app(
        self,
        mock_get_latest_app,
        mock_get_project,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
        mock_workflow_run,
        mock_from_workflow_run,
        mock_create_deploy_workflow_jobs,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        project = MagicMock(spec=Project, destroy_in_progress=False, id="user_id")
        mock_get_project.return_value = project
        app = MagicMock(spec=AppDeployment)
        mock_get_latest_app.return_value = app

        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DEPLOY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance

        mock_from_workflow_run.return_value = MagicMock(
            model_dump=MagicMock(return_value={"id": "deployment_id"})
        )
        common_job = MagicMock()
        mock_create_deploy_workflow_jobs.return_value = common_job

        # Act
        response = await install_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_get_project.assert_called_once_with("user_id")
        mock_get_latest_app.assert_called_once_with(project_id="user_id", app_id="app1")
        mock_bg.add_task.assert_called_once_with(
            run_full_deploy_workflow, mock_wf_run_instance, common_job
        )
        mock_create_deploy_workflow_jobs.assert_called_once_with(
            mock_wf_run_instance,
            ["app1"],
        )
        mock_from_workflow_run.assert_called_once_with(mock_wf_run_instance)

        # Assert response
        self.assertEqual(201, response.status_code)
        self.assertEqual(b'{"id": "deployment_id"}', response.body)

    @patch("src.api.workflow_router.get_email")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.BackgroundTasks")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_version")
    async def test_install_app_uninstall_ongoing(
        self,
        mock_get_latest_app,
        mock_get_project,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        project = MagicMock(spec=Project, destroy_in_progress=True)
        mock_get_project.return_value = project

        response = await install_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_get_project.assert_called_once_with("user_id")
        mock_get_latest_app.assert_not_called()
        mock_bg.add_task.assert_not_called()

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.detail,
            "Tear down in progress",
        )

    @patch("src.api.workflow_router.create_destroy_workflow_jobs")
    @patch.object(WorkflowRunSummary, "from_workflow_run")
    @patch("src.api.workflow_router.WorkflowRun")
    @patch("src.api.workflow_router.get_email")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.BackgroundTasks")
    async def test_uninstall(
        self,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
        mock_workflow_run,
        mock_from_workflow_run,
        mock_create_destroy_workflow_jobs,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "project_id"
        mock_get_email.return_value = "users_email"
        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DESTROY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance
        mock_from_workflow_run.return_value = MagicMock(
            model_dump=MagicMock(return_value={"id": "deployment_id"})
        )
        common_job = MagicMock()
        mock_create_destroy_workflow_jobs.return_value = common_job

        # Act
        response = await uninstall_all_apps(MagicMock(), mock_bg)

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            run_full_destroy_workflow, mock_wf_run_instance, common_job
        )
        mock_create_destroy_workflow_jobs.assert_called_once_with(
            mock_wf_run_instance, list(self.project.apps.keys())
        )
        mock_from_workflow_run.assert_called_once_with(mock_wf_run_instance)

        # Assert response
        self.assertEqual(201, response.status_code)
        self.assertEqual(b'{"id": "deployment_id"}', response.body)

    @patch("src.api.workflow_router.create_destroy_workflow_jobs")
    @patch.object(WorkflowRunSummary, "from_workflow_run")
    @patch("src.api.workflow_router.WorkflowRun")
    @patch("src.api.workflow_router.get_email")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.BackgroundTasks")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    async def test_uninstall_app(
        self,
        mock_get_latest_app,
        mock_get_project,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
        mock_workflow_run,
        mock_from_workflow_run,
        mock_create_destroy_workflow_jobs,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        project = MagicMock(spec=Project)
        mock_get_project.return_value = project
        app = MagicMock(spec=AppDeployment)
        mock_get_latest_app.return_value = app

        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DEPLOY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance

        mock_from_workflow_run.return_value = MagicMock(
            model_dump=MagicMock(return_value={"id": "deployment_id"})
        )
        common_job = MagicMock()
        mock_create_destroy_workflow_jobs.return_value = common_job

        # Act
        response = await uninstall_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_project.assert_called_once_with("user_id")
        mock_bg.add_task.assert_called_once_with(
            run_full_destroy_workflow,
            mock_wf_run_instance,
            common_job,
        )
        mock_create_destroy_workflow_jobs.assert_called_once_with(
            mock_wf_run_instance, ["app1"], False
        )
        mock_from_workflow_run.assert_called_once_with(mock_wf_run_instance)

        # Assert response
        self.assertEqual(201, response.status_code)
        self.assertEqual(b'{"id": "deployment_id"}', response.body)

    @patch("src.api.workflow_router.WorkflowJob")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.DeploymentDir")
    async def test_stream_deployment_logs(
        self, mock_deploy_dir_ctor, mock_get_user_id, mock_job
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_deploy_dir = MagicMock()
        mock_deploy_dir_ctor.return_value = mock_deploy_dir
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.tail.return_value = MagicMock()
        mock_job.get.return_value = MagicMock(modified_app_id="app_id")

        response: EventSourceResponse = await stream_deployment_logs(
            MagicMock(),
            run_number="1",
            job_number=1,
            workflow_type=WorkflowType.DEPLOY.value,
        )

        # Assert calls
        mock_deploy_dir_ctor.assert_called_once_with(
            "user_id", "user_id#DEPLOY##00000001"
        )
        mock_deploy_dir.get_log.assert_called_once_with("app_id")
        mock_deploy_log.tail.assert_called_once()

        # Assert response
        self.assertEqual(200, response.status_code)
