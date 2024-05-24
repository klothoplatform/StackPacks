import subprocess
from unittest.mock import MagicMock, patch

import aiounittest

from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.pulumi.builder import AppBuilder
from src.util.tmp import TempDir


class TestAppBuilder(aiounittest.AsyncTestCase):

    @patch("src.deployer.pulumi.builder.auto.create_or_select_stack")
    @patch("src.deployer.pulumi.builder.subprocess.run")
    @patch("src.deployer.pulumi.builder.zipfile.ZipFile")
    def test_prepare_stack(
        self,
        mock_zip_file,
        mock_run,
        mock_create_or_select_stack,
    ):
        # Setup mock objects
        builder = AppBuilder("tmp_dir", "test_bucket")

        builder.install_npm_deps = MagicMock()
        mock_return_stack = MagicMock()
        builder.create_pulumi_stack = MagicMock(return_value=mock_return_stack)

        # Call the method
        stack = builder.prepare_stack(MagicMock())

        # Assert calls
        builder.install_npm_deps.assert_called_once()
        builder.create_pulumi_stack.assert_called_once()

        # Assert return value
        self.assertEqual(stack, mock_return_stack)

    @patch("src.deployer.pulumi.builder.auto.ConfigValue")
    def test_configure_aws(self, mock_config_value):
        # Setup mock objects
        mock_config_value.side_effect = lambda x: x  # Return the string value
        mock_stack = MagicMock()

        # Call the method
        builder = AppBuilder(MagicMock(), "test_bucket")
        builder.configure_aws(
            mock_stack, role_arn="arn", region="region", external_id="external_id"
        )

        # Assert calls
        self.assertEqual(len(mock_stack.mock_calls), 3)
        self.assertEqual(mock_stack.set_config.call_count, 3)
        mock_stack.set_config.assert_any_call("aws:region", "region")

        mock_stack.set_config.assert_any_call(
            "aws:assumeRole.roleArn", "arn", path=True
        )
        mock_stack.set_config.assert_any_call(
            "aws:assumeRole.externalId", "external_id", path=True
        )

    @patch("src.deployer.pulumi.builder.auto.create_or_select_stack")
    def test_create_pulumi_stack(self, mock_create_or_select_stack):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_create_or_select_stack.return_value = mock_stack
        mock_job = MagicMock(
            spec=WorkflowJob,
            modified_app_id=MagicMock(return_value="app_id"),
        )
        # Call the method
        with TempDir() as tmp_dir:
            builder = AppBuilder(tmp_dir, "test_bucket")
            stack = builder.create_pulumi_stack(mock_job)

        # Assert call
        mock_create_or_select_stack.assert_called_once()
        self.assertEqual(
            mock_create_or_select_stack.call_args.kwargs[
                "opts"
            ].project_settings.backend.url,
            f"s3://{builder.state_bucket_name}",
        )

        # Assert return value
        self.assertEqual(stack, mock_stack)

    @patch("src.deployer.pulumi.builder.auto.create_or_select_stack")
    def test_create_pulumi_stack_no_bucket_name(self, mock_create_or_select_stack):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_create_or_select_stack.return_value = mock_stack
        mock_job = MagicMock(
            spec=WorkflowJob,
            modified_app_id=MagicMock(return_value="app_id"),
        )
        # Call the method
        with TempDir() as tmp_dir:
            builder = AppBuilder(tmp_dir, None)
            stack = builder.create_pulumi_stack(mock_job)

        # Assert call
        mock_create_or_select_stack.assert_called_once()
        self.assertIsNone(mock_create_or_select_stack.call_args.kwargs["opts"])

        # Assert return value
        self.assertEqual(stack, mock_stack)

    @patch("src.deployer.pulumi.builder.subprocess.run")
    def test_install_npm_deps(self, mock_run):
        mock_result = MagicMock()
        mock_run.return_value = mock_result
        mock_job = MagicMock(
            spec=WorkflowJob,
            modified_app_id=MagicMock(return_value="app_id"),
        )
        # Call the method
        with TempDir() as tmp_dir:
            builder = AppBuilder(tmp_dir, None)
            builder.install_npm_deps(mock_job)

        # Assert call
        mock_run.assert_called_once_with(
            ["npm", "install", "--prefix", builder.output_dir],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        mock_result.check_returncode.assert_called_once()
