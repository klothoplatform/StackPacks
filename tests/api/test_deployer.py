import aiounittest
from unittest.mock import patch, MagicMock

from fastapi.responses import StreamingResponse
from src.deployer.destroy import tear_down_pack
from src.deployer.deploy import deploy_pack
from src.api.deployer import (
    install,
    tear_down,
    stream_deployment_logs,
)
from src.stack_pack import StackPack


async def read_streaming_response(response):
    content = ""
    async for chunk in response.body_iterator:
        content += chunk
    return content


class TestRoutes(aiounittest.AsyncTestCase):
    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.Worker")
    @patch("src.api.deployer.get_stack_packs")
    async def test_install(
        self,
        mock_get_stack_packs,
        mock_worker,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        
        worker = MagicMock()
        mock_worker.return_value = worker
        sp = MagicMock(spec=StackPack)
        mock_get_stack_packs.return_value = {"a": sp}

        response = await install(
            MagicMock(),
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_worker.assert_called_once_with(target=deploy_pack, args=("user_id", {"a": sp}))
        worker.start.assert_called_once()

        # Assert response
        self.assertEqual(response, {"message": "Deployment started"})

    @patch("src.api.deployer.get_user_id")
    @patch("src.api.deployer.Worker")
    async def test_tear_down(
        self,
        mock_worker,
        mock_get_user_id,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        
        worker = MagicMock()
        mock_worker.return_value = worker

        response = await tear_down(
            MagicMock(),
        )

        # Assert calls
        mock_get_user_id.assert_called_once()
        mock_worker.assert_called_once_with(target=tear_down_pack, args=("user_id"))
        worker.start.assert_called_once()

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
