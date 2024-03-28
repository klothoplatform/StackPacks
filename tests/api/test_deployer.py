from unittest.mock import MagicMock, patch

import aiounittest
from fastapi.responses import StreamingResponse

from src.api.deployer import (
    install,
    install_app,
    tear_down,
    tear_down_app,
)
from src.deployer.deploy import (
    execute_deployment_workflow,
    execute_deploy_single_workflow,
)
from src.deployer.destroy import (
    execute_destroy_all_workflow,
    execute_destroy_single_workflow,
)
from src.stack_pack import StackPack
from src.stack_pack.models.app_deployment import AppDeployment
from src.stack_pack.models.project import Project


class TestRoutes(aiounittest.AsyncTestCase):
    @patch("src.api.deployer.get_email")
    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.BackgroundTasks")
    @patch("src.api.deployer.get_stack_packs")
    @patch("src.api.deployer.uuid")
    async def test_install(
        self,
        mock_uuid,
        mock_get_stack_packs,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"

        sp = MagicMock(spec=StackPack)
        mock_get_stack_packs.return_value = {"a": sp}

        response = await install(
            MagicMock(),
            mock_bg,
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            execute_deployment_workflow,
            "user_id",
            {"a": sp},
            "deployment_id",
            "users_email",
        )

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Deployment started","deployment_id":"deployment_id"}',
        )

    @patch("src.api.deployer.get_email")
    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.BackgroundTasks")
    @patch("src.api.deployer.uuid")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_version")
    async def test_install_app(
        self,
        mock_get_latest_app,
        mock_get_pack,
        mock_uuid,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        user_pack = MagicMock(spec=Project, tear_down_in_progress=False)
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=AppDeployment)
        mock_get_latest_app.return_value = user_app

        response = await install_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_latest_app.assert_called_once_with("user_id#app1")
        mock_bg.add_task.assert_called_once_with(
            execute_deploy_single_workflow,
            user_pack,
            user_app,
            "deployment_id",
            "users_email",
        )

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Deployment started","deployment_id":"deployment_id"}',
        )

    @patch("src.api.deployer.get_email")
    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.BackgroundTasks")
    @patch("src.api.deployer.uuid")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_version")
    async def test_install_app_tear_down_ongoing(
        self,
        mock_get_latest_app,
        mock_get_pack,
        mock_uuid,
        mock_bg,
        mock_get_user_id,
        mock_get_email,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"
        mock_get_email.return_value = "users_email"
        user_pack = MagicMock(spec=Project, tear_down_in_progress=True)
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=AppDeployment)

        response = await install_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_email.assert_called_once()
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_latest_app.assert_not_called()
        mock_bg.add_task.assert_not_called()

        # Assert response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.detail,
            "Tear down in progress",
        )

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.BackgroundTasks")
    @patch("src.api.deployer.uuid")
    async def test_tear_down(
        self,
        mock_uuid,
        mock_bg,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"

        response = await tear_down(MagicMock(), mock_bg)

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            execute_destroy_all_workflow, "user_id", "deployment_id"
        )

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Destroy started","deployment_id":"deployment_id"}',
        )

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.BackgroundTasks")
    @patch("src.api.deployer.uuid")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    async def test_tear_down_app(
        self,
        mock_get_latest_app,
        mock_get_pack,
        mock_uuid,
        mock_bg,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"
        user_pack = MagicMock(spec=Project)
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=AppDeployment)
        mock_get_latest_app.return_value = user_app

        response = await tear_down_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_latest_app.assert_called_once_with("user_id#app1")
        mock_bg.add_task.assert_called_once_with(
            execute_destroy_single_workflow, user_pack, user_app, "deployment_id"
        )
        user_pack.update.assert_called_once_with(
            actions=[Project.destroy_in_progress.set(True)]
        )

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Destroy started","deployment_id":"deployment_id"}',
        )

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.BackgroundTasks")
    @patch("src.api.deployer.uuid")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    async def test_tear_down_app_wont_destroy_common(
        self,
        mock_get_latest_app,
        mock_get_pack,
        mock_uuid,
        mock_bg,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"
        user_pack = MagicMock(
            spec=Project, apps={"app1": 1, Project.COMMON_APP_NAME: 1, "app2": 1}
        )
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=AppDeployment)
        mock_get_latest_app.return_value = user_app

        response = await tear_down_app(
            MagicMock(),
            mock_bg,
            "app1",
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_latest_app.assert_called_once_with("user_id#app1")
        mock_bg.add_task.assert_called_once_with(
            execute_destroy_single_workflow, user_pack, user_app, "deployment_id"
        )
        user_pack.update.assert_not_called()

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Destroy started","deployment_id":"deployment_id"}',
        )
