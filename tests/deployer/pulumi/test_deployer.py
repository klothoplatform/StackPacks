from unittest.mock import MagicMock, patch

import aiounittest

from src.deployer.models.deployment import DeploymentStatus
from src.deployer.pulumi.deployer import AppDeployer


class TestAppDeployer(aiounittest.AsyncTestCase):
    @patch("src.deployer.pulumi.deployer.auto.UpResult")
    async def test_deploy(self, mock_up_result):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.preview.return_value = "preview_result"
        mock_stack.up.return_value = mock_up_result
        mock_up_result.outputs.items.return_value = "outputs"

        # Call the method
        deployer = AppDeployer(mock_stack)
        result_status, reason = await deployer.deploy()

        # Assert calls
        mock_stack.preview.assert_called_once()
        mock_stack.up.assert_called_once()

        # Assert return value
        self.assertEqual(result_status, DeploymentStatus.SUCCEEDED)
        self.assertEqual(reason, "Deployment succeeded.")

    @patch("src.deployer.pulumi.deployer.auto.UpResult")
    async def test_deploy_error(self, mock_up_result):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.preview.side_effect = Exception("preview error")

        # Call the method
        deployer = AppDeployer(mock_stack)
        result_status, reason = await deployer.deploy()

        # Assert calls and return value
        mock_stack.preview.assert_called_once()
        mock_stack.up.assert_not_called()
        self.assertEqual(result_status, DeploymentStatus.FAILED)
        self.assertEqual(reason, "preview error")

    async def test_destroy_and_remove_stack(self):
        # Setup mock objects
        mock_stack = MagicMock()

        # Call the method
        deployer = AppDeployer(mock_stack)
        result_status, reason = await deployer.destroy_and_remove_stack()

        # Assert calls
        mock_stack.destroy.assert_called_once()
        mock_stack.workspace.remove_stack.assert_called_once_with(mock_stack.name)

        # Assert return value
        self.assertEqual(result_status, DeploymentStatus.SUCCEEDED)
        self.assertEqual(reason, "Stack removed successfully.")

    async def test_destroy_and_remove_stack_error(self):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.destroy.side_effect = Exception("destroy error")

        # Call the method
        deployer = AppDeployer(mock_stack)
        result_status, reason = await deployer.destroy_and_remove_stack()

        # Assert calls and return value
        mock_stack.destroy.assert_called_once()
        mock_stack.workspace.remove_stack.assert_not_called()
        self.assertEqual(result_status, DeploymentStatus.FAILED)
        self.assertEqual(reason, "destroy error")
