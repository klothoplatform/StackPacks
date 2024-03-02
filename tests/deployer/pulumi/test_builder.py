import os
import aiounittest
from unittest.mock import call, patch, MagicMock, mock_open, ANY
from src.deployer.pulumi.builder import (
    AppBuilder,
)  # replace with your actual module name
from pulumi import automation as auto
import subprocess


class TestAppBuilder(aiounittest.AsyncTestCase):

    def setUp(self) -> None:
        self.mock_sts_client = MagicMock()
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    @patch("src.deployer.pulumi.builder.auto.create_or_select_stack")
    @patch("src.deployer.pulumi.builder.subprocess.run")
    @patch("src.deployer.pulumi.builder.zipfile.ZipFile")
    @patch("src.deployer.pulumi.builder.io.BytesIO")
    def test_prepare_stack(
        self,
        mock_bytes_io,
        mock_zip_file,
        mock_run,
        mock_create_or_select_stack,
    ):
        # Setup mock objects
        builder = AppBuilder(self.mock_sts_client)
        builder.create_output_dir = MagicMock()

        builder.install_npm_deps = MagicMock()
        mock_return_stack = MagicMock()
        builder.create_pulumi_stack = MagicMock(return_value=mock_return_stack)

        # Call the method
        stack = builder.prepare_stack(b"iac", MagicMock())

        # Assert calls
        builder.create_output_dir.assert_called_once_with(b"iac")
        builder.install_npm_deps.assert_called_once()
        builder.create_pulumi_stack.assert_called_once()

        # Assert return value
        self.assertEqual(stack, mock_return_stack)

    def test_exit(self):
        # Call the method
        builder = AppBuilder(MagicMock())
        builder.tmpdir = MagicMock()
        builder.__exit__(None, None, None)

        # Assert call
        builder.tmpdir.__exit__.assert_called_once()

    @patch("src.deployer.pulumi.builder.auto.ConfigValue")
    def test_configure_aws(self, mock_config_value):
        # Setup mock objects
        mock_config_value.side_effect = lambda x: x  # Return the string value
        mock_stack = MagicMock()

        # Call the method
        builder = AppBuilder(MagicMock())
        builder.configure_aws(mock_stack, "arn", "region")

        # Assert calls
        self.assertEqual(len(mock_stack.mock_calls), 2)
        self.assertEqual(mock_stack.set_config.call_count, 2)
        mock_stack.set_config.assert_any_call("aws:region", "region")
        mock_stack.set_config.assert_any_call(
            "roleArn", "arn", path="aws:assumeRole.roleArn"
        )

    @patch("src.deployer.pulumi.builder.auto.create_or_select_stack")
    def test_create_pulumi_stack(self, mock_create_or_select_stack):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_create_or_select_stack.return_value = mock_stack

        # Call the method
        with AppBuilder(self.mock_sts_client) as builder:
            stack = builder.create_pulumi_stack(MagicMock())

        # Assert call
        mock_create_or_select_stack.assert_called_once()

        # Assert return value
        self.assertEqual(stack, mock_stack)

    @patch("src.deployer.pulumi.builder.subprocess.run")
    def test_install_npm_deps(self, mock_run):
        mock_result = MagicMock()
        mock_run.return_value = mock_result
        # Call the method
        with AppBuilder(MagicMock()) as builder:
            builder.install_npm_deps()

        # Assert call
        mock_run.assert_called_once_with(
            ["npm", "install", "--prefix", builder.output_dir],
            stdout=subprocess.DEVNULL,
        )
        mock_result.check_returncode.assert_called_once()
