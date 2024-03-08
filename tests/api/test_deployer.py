from unittest.mock import MagicMock, patch

import aiounittest
from fastapi.responses import StreamingResponse

from src.api.deployer import install, stream_deployment_logs, tear_down
from src.deployer.deploy import deploy_pack
from src.deployer.destroy import tear_down_pack
from src.stack_pack import StackPack


class TestRoutes(aiounittest.AsyncTestCase):
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
    ):
        # Setup mock objects
        mock_uuid.uuid4.return_value = "deployment_id"
        mock_get_user_id.return_value = "user_id"

        sp = MagicMock(spec=StackPack)
        mock_get_stack_packs.return_value = {"a": sp}

        response = await install(
            MagicMock(),
            mock_bg,
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_bg.add_task.assert_called_once_with(
            deploy_pack, "user_id", {"a": sp}, "deployment_id"
        )

        # Assert response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.body,
            b'{"message":"Deployment started","deployment_id":"deployment_id"}',
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
        mock_bg.add_task.assert_called_once_with(tear_down_pack, "user_id")

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
        mock_deploy_dir.get_log.assert_called_once_with("user_id_app_id")
        mock_deploy_log.tail.assert_called_once()

        # Assert response
        self.assertEqual(response.status_code, 200)
