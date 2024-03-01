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
    @patch("src.deployer.pulumi.builder.assume_role")
    @patch("src.deployer.pulumi.builder.subprocess.run")
    @patch("src.deployer.pulumi.builder.zipfile.ZipFile")
    @patch("src.deployer.pulumi.builder.io.BytesIO")
    @patch("src.deployer.pulumi.builder.tempfile.mkdtemp")
    def test_prepare_stack(
        self,
        mock_mkdtemp,
        mock_bytes_io,
        mock_zip_file,
        mock_run,
        mock_assume_role,
        mock_create_or_select_stack,
    ):
        # Setup mock objects
        mock_mkdtemp.return_value = "/tmp/tempdir"
        builder = AppBuilder(self.mock_sts_client)
        builder.create_output_dir = MagicMock()
        builder.install_npm_deps = MagicMock()
        mock_return_stack = MagicMock()
        builder.create_pulumi_stack = MagicMock(return_value=mock_return_stack)

        # Call the method
        stack = builder.prepare_stack(b"iac", MagicMock())

        # Assert calls
        mock_mkdtemp.assert_called_once()
        builder.create_output_dir.assert_called_once_with(b"iac")
        builder.install_npm_deps.assert_called_once()
        builder.create_pulumi_stack.assert_called_once()

        # Assert return value
        self.assertEqual(stack, mock_return_stack)

    @patch("src.deployer.pulumi.builder.shutil.rmtree")
    def test_exit(self, mock_rmtree):
        # Call the method
        builder = AppBuilder(MagicMock())
        builder.__exit__(None, None, None)

        # Assert call
        mock_rmtree.assert_called_once_with(builder.output_dir)

    @patch("src.deployer.pulumi.builder.assume_role")
    @patch("src.deployer.pulumi.builder.auto.ConfigValue")
    def test_configure_aws(self, mock_config_value, mock_assume_role):
        # Setup mock objects
        mock_config_value.side_effect = lambda x: x  # Return the string value
        mock_stack = MagicMock()
        mock_creds = MagicMock(
            AccessKeyId="test_access_key_id",
            SecretAccessKey="test_secret_access_key",
            SessionToken="test_session_token",
        )
        mock_assume_role.return_value = (mock_creds, MagicMock())

        # Call the method
        builder = AppBuilder(MagicMock())
        builder.configure_aws(mock_stack, "arn", "region")

        # Assert calls
        mock_assume_role.assert_called_once_with(builder.sts_client, "arn")
        self.assertEqual(len(mock_stack.mock_calls), 4)
        self.assertEqual(mock_stack.set_config.call_count, 4)
        mock_stack.set_config.assert_any_call("aws:region", "region")
        mock_stack.set_config.assert_any_call("aws:accessKey", mock_creds.AccessKeyId)
        mock_stack.set_config.assert_any_call(
            "aws:secretKey", mock_creds.SecretAccessKey
        )
        mock_stack.set_config.assert_any_call("aws:token", mock_creds.SessionToken)

    @patch("src.deployer.pulumi.builder.auto.create_or_select_stack")
    def test_create_pulumi_stack(self, mock_create_or_select_stack):
        # Setup mock objects
        mock_stack = MagicMock()
        mock_create_or_select_stack.return_value = mock_stack

        # Call the method
        builder = AppBuilder(self.mock_sts_client)
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
        builder = AppBuilder(MagicMock())
        builder.install_npm_deps()

        # Assert call
        mock_run.assert_called_once_with(
            ["npm", "install", "--prefix", builder.output_dir],
            stdout=subprocess.DEVNULL,
        )
        mock_result.check_returncode.assert_called_once()
