import aiounittest
from unittest.mock import patch, MagicMock

from fastapi.responses import StreamingResponse
from src.api.deployer import (
    install,
    tear_down,
    stream_deployment_logs,
    DeploymentRequest,
)


async def read_streaming_response(response):
    content = ""
    async for chunk in response.body_iterator:
        content += chunk
    return content


class TestRoutes(aiounittest.AsyncTestCase):
    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.Process")
    @patch("src.api.deployer.read_zip_to_bytes")
    async def test_install(
        self, mock_read_zip_to_bytes, mock_process, mock_get_user_id
    ):
        # Setup mock objects
        mock_read_zip_to_bytes.return_value = b"iac"
        mock_get_user_id.return_value = "user_id"
        mock_process.return_value = MagicMock()

        response = await install(
            MagicMock(),
            DeploymentRequest(
                region="region",
                assume_role_arn="arn",
                packages=["package1", "package2"],
            ),
        )

        # Assert calls
        mock_read_zip_to_bytes.assert_called_once_with(
            "/Users/jordansinger/workspace/StackPacks/untitled_architecture_default (2).zip"
        )
        mock_get_user_id.assert_called_once()
        mock_process.assert_called_once()
        mock_process.return_value.start.assert_called_once()

        # Assert response
        self.assertEqual(response, {"message": "Deployment started"})

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.Process")
    @patch("src.api.deployer.read_zip_to_bytes")
    async def test_tear_down(
        self, mock_read_zip_to_bytes, mock_process, mock_get_user_id
    ):
        # Setup mock objects
        mock_read_zip_to_bytes.return_value = b"iac"
        mock_get_user_id.return_value = "user_id"
        mock_process.return_value = MagicMock()

        response = await tear_down(
            MagicMock(),
            DeploymentRequest(
                region="region",
                assume_role_arn="arn",
                packages=["package1", "package2"],
            ),
        )

        # Assert calls
        mock_read_zip_to_bytes.assert_called_once_with(
            "/Users/jordansinger/workspace/StackPacks/untitled_architecture_default (2).zip"
        )
        mock_get_user_id.assert_called_once()
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
