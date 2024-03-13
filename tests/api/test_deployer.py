from unittest.mock import MagicMock, patch

import aiounittest
from fastapi.responses import StreamingResponse

from src.api.deployer import (
    install,
    install_app,
    stream_deployment_logs,
    tear_down,
    tear_down_app,
)
from src.deployer.deploy import deploy_pack, deploy_single
from src.deployer.destroy import tear_down_pack, tear_down_single
from src.stack_pack import StackPack
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack


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
            deploy_pack, "user_id", {"a": sp}, "deployment_id", "users_email"
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
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get_latest_version")
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
        user_pack = MagicMock(spec=UserPack, tear_down_in_progress=False)
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=UserApp)
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
            deploy_single, user_pack, user_app, "deployment_id", "users_email"
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
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get_latest_version")
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
        user_pack = MagicMock(spec=UserPack, tear_down_in_progress=True)
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=UserApp)

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
            tear_down_pack, "user_id", "deployment_id"
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
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get_latest_version_with_status")
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
        user_pack = MagicMock(spec=UserPack)
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=UserApp)
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
            tear_down_single, user_pack, user_app, "deployment_id"
        )
        user_pack.update.assert_called_once_with(
            actions=[UserPack.tear_down_in_progress.set(True)]
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
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get_latest_version_with_status")
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
            spec=UserPack, apps={"app1": 1, UserPack.COMMON_APP_NAME: 1, "app2": 1}
        )
        mock_get_pack.return_value = user_pack
        user_app = MagicMock(spec=UserApp)
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
            tear_down_single, user_pack, user_app, "deployment_id"
        )
        user_pack.update.assert_not_called()

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Destroy started","deployment_id":"deployment_id"}',
        )

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.DeploymentDir")
    async def test_stream_deployment_logs(self, mock_deploy_dir_ctor, mock_get_user_id):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_deploy_dir = MagicMock()
        mock_deploy_dir_ctor.return_value = mock_deploy_dir
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.tail.return_value = MagicMock()

        response: StreamingResponse = await stream_deployment_logs(
            MagicMock(), "deployment_id", "app_id"
        )

        # Assert calls
        mock_deploy_dir_ctor.assert_called_once_with("user_id", "deployment_id")
        mock_deploy_dir.get_log.assert_called_once_with("app_id")
        mock_deploy_log.tail.assert_called_once()

        # Assert response
        self.assertEqual(response.status_code, 200)
