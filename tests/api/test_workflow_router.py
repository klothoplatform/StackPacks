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
from src.deployer.deploy import (
    execute_deploy_single_workflow,
    execute_deployment_workflow,
)
from src.deployer.destroy import (
    execute_destroy_all_workflow,
    execute_destroy_single_workflow,
)
from src.deployer.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowType,
)
from src.project import StackPack
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project


class TestWorkflowRouter(aiounittest.AsyncTestCase):

    @patch("src.api.workflow_router.WorkflowRunSummary")
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
        mock_wf_run_summary,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"

        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DEPLOY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance

        mock_wf_run_summary.from_workflow_run.return_value = MagicMock(
            spec=WorkflowRunSummary, dict=lambda: {"id": "deployment_id"}
        )

        sp = MagicMock(spec=StackPack)

        response = await install(
            MagicMock(),
            mock_bg,
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            execute_deployment_workflow,
            mock_wf_run_instance,
        )

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            b'{"id": "deployment_id"}',
            response.body,
        )

    @patch("src.api.workflow_router.WorkflowRunSummary")
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
        mock_wf_run_summary,
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

        mock_wf_run_summary.from_workflow_run.return_value = MagicMock(
            spec=WorkflowRunSummary, dict=lambda: {"id": "deployment_id"}
        )

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
            execute_deploy_single_workflow,
            mock_wf_run_instance,
        )

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

    @patch("src.api.workflow_router.WorkflowRunSummary")
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
        mock_wf_run_summary,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DESTROY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance
        mock_wf_run_summary.from_workflow_run.return_value = MagicMock(
            spec=WorkflowRunSummary, dict=lambda: {"id": "deployment_id"}
        )

        # Act
        response = await uninstall_all_apps(MagicMock(), mock_bg)

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            execute_destroy_all_workflow, mock_wf_run_instance
        )

        # Assert response
        self.assertEqual(201, response.status_code)
        self.assertEqual(b'{"id": "deployment_id"}', response.body)

    @patch("src.api.workflow_router.WorkflowRunSummary")
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
        mock_wf_run_summary,
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

        mock_wf_run_summary.from_workflow_run.return_value = MagicMock(
            spec=WorkflowRunSummary, dict=lambda: {"id": "deployment_id"}
        )

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
            execute_destroy_single_workflow,
            mock_wf_run_instance,
            True,
        )
        project.update.assert_called_once_with(
            actions=[Project.destroy_in_progress.set(True)]
        )

        # Assert response
        self.assertEqual(201, response.status_code)
        self.assertEqual(b'{"id": "deployment_id"}', response.body)

    @patch("src.api.workflow_router.WorkflowRunSummary")
    @patch("src.api.workflow_router.WorkflowRun")
    @patch("src.api.workflow_router.get_email")
    @patch("src.api.workflow_router.get_user_id")
    @patch("src.api.workflow_router.BackgroundTasks")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    async def test_uninstall_app_wont_destroy_common(
        self,
        mock_get_latest_app,
        mock_get_project,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
        mock_workflow_run,
        mock_wf_run_summary,
    ):
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        project = MagicMock(
            spec=Project, apps={"app1": 1, Project.COMMON_APP_NAME: 1, "app2": 1}
        )
        mock_get_project.return_value = project
        app = MagicMock(spec=AppDeployment)

        def get_latest(_project_id, app_id):
            if app_id in [Project.COMMON_APP_NAME, "app2"]:
                return MagicMock()
            elif app_id == "app1":
                return app
            return None

        mock_get_latest_app.side_effect = get_latest

        mock_wf_run_instance = MagicMock(
            spec=WorkflowRun,
            type=WorkflowType.DEPLOY.value,
            status=WorkflowRunStatus.NEW.value,
        )
        mock_workflow_run.create.return_value = mock_wf_run_instance

        mock_wf_run_summary.from_workflow_run.return_value = MagicMock(
            spec=WorkflowRunSummary, dict=lambda: {"id": "deployment_id"}
        )

        # Act
        response = await uninstall_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_get_project.assert_called_once_with("user_id")
        mock_bg.add_task.assert_called_once_with(
            execute_destroy_single_workflow, mock_wf_run_instance, False
        )
        project.update.assert_not_called()

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
