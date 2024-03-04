from asyncio import AbstractEventLoop
import aiounittest
from unittest.mock import ANY, patch, MagicMock, AsyncMock
from src.deployer.main import (
    run_build_and_deploy,
    run_destroy_loop,
    build_and_deploy,
    run_destroy,
)


class MockEventLoop(MagicMock, AbstractEventLoop):
    def __init__(self):
        super().__init__()
        self.run_until_complete = MagicMock()
        self.close = MagicMock()


class TestMyModule(aiounittest.AsyncTestCase):
    @patch("asyncio.new_event_loop", return_value=MockEventLoop())
    @patch("asyncio.set_event_loop")
    @patch("src.deployer.main.build_and_deploy", new_callable=AsyncMock)
    def test_run_build_and_deploy(
        self, mock_build_and_deploy, mock_set_event_loop, mock_new_event_loop
    ):
        mock_build_and_deploy.return_value = MagicMock()
        mock_loop = mock_new_event_loop.return_value

        # Call the function to test
        cfg = {}
        tmp_dir = MagicMock()
        tmp_dir.dir = "/tmp"
        run_build_and_deploy(None, "region", "arn", "user", b"iac", cfg, tmp_dir)

        # Check that a new event loop was created and set
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()
        tmp_dir.cleanup.assert_called_once()

        # Check that build_and_deploy was called with the correct arguments
        mock_build_and_deploy.assert_called_once_with(
            None, "region", "arn", "user", b"iac", cfg, tmp_dir.dir
        )

    @patch("src.deployer.main.AppDeployer")
    @patch("src.deployer.main.Deployment")
    @patch("src.deployer.main.PulumiStack")
    async def test_build_and_deploy(
        self,
        mock_pulumi_stack,
        mock_deployment,
        mock_app_deployer,
    ):
        # Setup mock objects
        mock_queue = MagicMock()
        mock_queue.put = AsyncMock()

        with (
            patch("src.deployer.main.AppBuilder") as AppBuilder,
            patch("src.deployer.pulumi.builder.auto.ConfigValue") as auto_config_value,
        ):
            mock_builder = AppBuilder.return_value

            auto_config_value.side_effect = lambda v, secret: v

            mock_deployer = MagicMock()
            mock_app_deployer.return_value = mock_deployer
            mock_deployer.deploy = AsyncMock(return_value=(MagicMock(), "reason"))

            # Call the method
            cfg = {"key": "value"}
            await build_and_deploy(
                mock_queue, "region", "arn", "user", b"iac", cfg, "/tmp"
            )

            # Assert calls
            mock_pulumi_stack.assert_called_once_with(
                project_name="StackPack",
                name=mock_pulumi_stack.sanitize_stack_name.return_value,
                status="IN_PROGRESS",
                status_reason="Deployment in progress",
                created_by="user",
            )
            mock_deployment.assert_called_once_with(
                id=ANY,
                iac_stack_composite_key=mock_pulumi_stack.return_value.composite_key.return_value,
                action="DEPLOY",
                status="IN_PROGRESS",
                status_reason="Deployment in progress",
                initiated_by="user",
            )
            AppBuilder.assert_called_once_with("/tmp")
            mock_builder.prepare_stack.assert_called_once_with(
                b"iac", mock_pulumi_stack.return_value
            )
            mock_builder.configure_aws.assert_called_once_with(
                mock_builder.prepare_stack.return_value, "arn", "region"
            )
            mock_app_deployer.assert_called_once_with(
                mock_builder.prepare_stack.return_value
            )
            for k, v in cfg.items():
                mock_builder.prepare_stack.return_value.set_config.assert_called_once_with(
                    k, v
                )
            mock_deployer.deploy.assert_called_once_with(mock_queue)
            mock_queue.put.assert_called_once_with("Done")
            mock_pulumi_stack.return_value.update.assert_called_once()
            mock_deployment.return_value.update.assert_called_once()

    @patch("asyncio.new_event_loop", return_value=MockEventLoop())
    @patch("asyncio.set_event_loop")
    @patch("src.deployer.main.run_destroy")
    def test_run_destroy_loop(
        self, mock_run_destroy, mock_set_event_loop, mock_new_event_loop
    ):

        mock_run_destroy.return_value = MagicMock()
        mock_loop = mock_new_event_loop.return_value

        cfg = {}
        tmp_dir = MagicMock()
        tmp_dir.dir = "/tmp"

        # Call the function to test
        run_destroy_loop(None, "region", "arn", "user", b"iac", cfg, tmp_dir)

        # Check that a new event loop was created and set
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()
        tmp_dir.cleanup.assert_called_once()

        # Check that build_and_deploy was called with the correct arguments
        mock_run_destroy.assert_called_once_with(
            None, "region", "arn", "user", b"iac", cfg, "/tmp"
        )

    @patch("src.deployer.main.AppDeployer")
    @patch("src.deployer.main.AppBuilder")
    @patch("src.deployer.main.Deployment")
    @patch("src.deployer.main.PulumiStack")
    async def test_run_destroy(
        self,
        mock_pulumi_stack,
        mock_deployment,
        mock_app_builder,
        mock_app_deployer,
    ):
        # Setup mock objects
        mock_queue = MagicMock()
        mock_queue.put = AsyncMock()
        mock_builder = MagicMock()
        mock_app_builder.return_value = mock_builder
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer
        mock_deployer.destroy_and_remove_stack = AsyncMock(
            return_value=(MagicMock(), "reason")
        )

        cfg = {}

        # Call the method
        await run_destroy(mock_queue, "region", "arn", "user", b"iac", cfg, "/tmp")

        # Assert calls
        mock_pulumi_stack.assert_called_once_with(
            project_name="StackPack",
            name=mock_pulumi_stack.sanitize_stack_name.return_value,
            status="IN_PROGRESS",
            status_reason="Destroy in progress",
            created_by="user",
        )
        mock_deployment.assert_called_once_with(
            id=ANY,
            iac_stack_composite_key=mock_pulumi_stack.return_value.composite_key.return_value,
            action="DESTROY",
            status="IN_PROGRESS",
            status_reason="Destroy in progress",
            initiated_by="user",
        )
        mock_app_builder.assert_called_once_with("/tmp")
        mock_builder.prepare_stack.assert_called_once_with(
            b"iac", mock_pulumi_stack.return_value
        )
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value, "arn", "region"
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value
        )
        mock_deployer.destroy_and_remove_stack.assert_called_once_with(mock_queue)
        mock_queue.put.assert_called_once_with("Done")
        mock_pulumi_stack.return_value.update.assert_called_once()
        mock_deployment.return_value.update.assert_called_once()
