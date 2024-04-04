from unittest.mock import MagicMock, patch

import aiounittest

from src.deployer.models.workflow_job import WorkflowJobStatus
from src.deployer.pulumi.deployer import AppDeployer


class TestAppDeployer(aiounittest.AsyncTestCase):
    @patch("src.deployer.pulumi.deployer.auto.UpResult")
    async def test_deploy(self, mock_up_result):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.name = "stack_name"
        mock_stack.preview.return_value = "preview_result"
        mock_stack.up.return_value = mock_up_result
        mock_up_result.outputs.items.return_value = "outputs"
        mock_deploy_dir = MagicMock()
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.on_output.return_value = MagicMock()

        # Call the method
        deployer = AppDeployer(mock_stack, mock_deploy_dir)
        result_status, reason = await deployer.deploy()

        # Assert calls
        mock_stack.preview.assert_called_once()
        mock_stack.up.assert_called_once()
        mock_deploy_dir.get_log.assert_called_once_with("stack_name")
        mock_deploy_log.on_output.assert_called_once()

        # Assert return value
        self.assertEqual(result_status, WorkflowJobStatus.SUCCEEDED)
        self.assertEqual(reason, "Deployment succeeded.")

    @patch("src.deployer.pulumi.deployer.auto.UpResult")
    async def test_deploy_error(self, mock_up_result):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.name = "stack_name"
        mock_stack.preview.side_effect = Exception("preview error")
        mock_deploy_dir = MagicMock()
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.on_output.return_value = MagicMock()

        # Call the method
        deployer = AppDeployer(mock_stack, mock_deploy_dir)
        result_status, reason = await deployer.deploy()

        # Assert calls and return value
        mock_stack.preview.assert_called_once()
        mock_stack.up.assert_not_called()
        mock_deploy_dir.get_log.assert_called_once_with("stack_name")
        mock_deploy_log.on_output.assert_called_once()

        self.assertEqual(result_status, WorkflowJobStatus.FAILED)
        self.assertEqual(reason, "preview error")

    async def test_destroy_and_remove_stack(self):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.name = "stack_name"
        mock_deploy_dir = MagicMock()
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.on_output.return_value = MagicMock()

        # Call the method
        deployer = AppDeployer(mock_stack, mock_deploy_dir)
        result_status, reason = await deployer.destroy_and_remove_stack()

        # Assert calls
        mock_stack.destroy.assert_called_once()
        mock_stack.workspace.remove_stack.assert_called_once_with(mock_stack.name)
        mock_deploy_dir.get_log.assert_called_once_with("stack_name")
        mock_deploy_log.on_output.assert_called_once()

        # Assert return value
        self.assertEqual(result_status, WorkflowJobStatus.SUCCEEDED)
        self.assertEqual(reason, "Stack removed successfully.")

    async def test_destroy_and_remove_stack_error(self):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_stack.name = "stack_name"
        mock_stack.destroy.side_effect = Exception("destroy error")
        mock_deploy_dir = MagicMock()
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.on_output.return_value = MagicMock()

        # Call the method
        deployer = AppDeployer(mock_stack, mock_deploy_dir)
        result_status, reason = await deployer.destroy_and_remove_stack()

        # Assert calls and return value
        mock_stack.destroy.assert_called_once()
        mock_stack.workspace.remove_stack.assert_not_called()
        mock_deploy_dir.get_log.assert_called_once_with("stack_name")
        mock_deploy_log.on_output.assert_called_once()

        self.assertEqual(result_status, WorkflowJobStatus.FAILED)
        self.assertEqual(reason, "destroy error")
