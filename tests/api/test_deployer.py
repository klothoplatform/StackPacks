import aiounittest
from unittest.mock import patch, MagicMock

from fastapi.responses import StreamingResponse
from src.api.deployer import (
    install,
    tear_down,
    stream_deployment_logs,
)


async def read_streaming_response(response):
    content = ""
    async for chunk in response.body_iterator:
        content += chunk
    return content


class TestRoutes(aiounittest.AsyncTestCase):
    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.Process")
    @patch("src.api.deployer.UserPack.get")
    @patch("src.api.deployer.get_iac_storage")
    @patch("src.api.deployer.get_stack_packs")
    async def test_install(
        self,
        mock_get_stack_packs,
        mock_iac_storage,
        mock_userpack_get,
        mock_process,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_userpack = MagicMock()
        mock_userpack.id = "user_id"
        mock_userpack.configuration = {"a": "b"}
        mock_userpack_get.return_value = mock_userpack
        mock_storage = MagicMock()
        mock_storage.get_iac.return_value = b"iac"
        mock_iac_storage.return_value = mock_storage
        mock_process.return_value = MagicMock()
        mock_config = MagicMock()
        mock_config.get_pulumi_configs.return_value = {"x": "y"}
        mock_get_stack_packs.return_value = {"a": mock_config}

        response = await install(
            MagicMock(),
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_userpack_get.assert_called_once_with("user_id", "user_id")
        mock_storage.get_iac.assert_called_once_with("user_id")
        mock_process.assert_called_once()
        mock_process.return_value.start.assert_called_once()

        # Assert response
        self.assertEqual(response, {"message": "Deployment started"})

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.Process")
    @patch("src.api.deployer.UserPack.get")
    @patch("src.api.deployer.get_iac_storage")
    @patch("src.api.deployer.get_stack_packs")
    async def test_tear_down(
        self,
        mock_get_stack_packs,
        mock_iac_storage,
        mock_userpack_get,
        mock_process,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_userpack = MagicMock()
        mock_userpack.id = "user_id"
        mock_userpack.configuration = {"a": "b"}
        mock_userpack_get.return_value = mock_userpack
        mock_storage = MagicMock()
        mock_storage.get_iac.return_value = b"iac"
        mock_iac_storage.return_value = mock_storage
        mock_process.return_value = MagicMock()
        mock_config = MagicMock()
        mock_config.get_pulumi_configs.return_value = {"x": "y"}
        mock_get_stack_packs.return_value = {"a": mock_config}

        response = await tear_down(
            MagicMock(),
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_userpack_get.assert_called_once_with("user_id", "user_id")
        mock_storage.get_iac.assert_called_once_with("user_id")
        mock_process.assert_called_once()
        mock_process.return_value.start.assert_called_once()

        # Assert response
        self.assertEqual(response, {"message": "Destroy started"})

    @patch("src.api.deployer.stream_deployment_events")
    async def test_stream_deployment_logs(self, mock_stream_deployment_events):
        # Setup mock objects
        mock_stream_deployment_events.return_value = iter(["event1", "event2"])

        response: StreamingResponse = await stream_deployment_logs(MagicMock(), "id")

        # Assert calls
        mock_stream_deployment_events.assert_called_once()

        # Assert response
        self.assertEqual(response.status_code, 200)
        body = await read_streaming_response(response)
        self.assertEqual(body, "event1event2")
