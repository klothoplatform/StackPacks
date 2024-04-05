from pathlib import Path
from unittest.mock import MagicMock, patch

import aiounittest

from src.deployer.pulumi.manager import AppManager
from src.engine_service.engine_commands.get_live_state import GetLiveStateRequest
from src.project.live_state import LiveState


class TestAppManager(aiounittest.AsyncTestCase):
    @patch("src.deployer.pulumi.manager.get_live_state")
    @patch("src.deployer.pulumi.manager.parse_yaml_raw_as")
    async def test_read_deployed_state(
        self, mock_parse_yaml_raw_as, mock_get_live_state
    ):
        # Arrange
        mock_stack = MagicMock()
        mock_stack.export_stack.return_value.deployment = {
            "resources": "mock_resources"
        }
        app_manager = AppManager(mock_stack)

        mock_get_live_state.return_value = "mock_resources_yaml"
        mock_parse_yaml_raw_as.return_value = "mock_live_state"

        # Act
        result = await app_manager.read_deployed_state(Path("mock_dir"))

        # Assert
        mock_get_live_state.assert_called_once_with(
            GetLiveStateRequest(state="mock_resources", tmp_dir="mock_dir")
        )
        mock_parse_yaml_raw_as.assert_called_once_with(LiveState, "mock_resources_yaml")
        self.assertEqual(result, "mock_live_state")
