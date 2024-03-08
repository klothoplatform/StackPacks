from asyncio import QueueEmpty
from unittest.mock import MagicMock, call, patch

import aiounittest

from src.deployer.pulumi.deploy_logs import (
    LOG_DIR,
    DeployLog,
    DeployLogHandler,
    DeploymentDir,
)


class TestDeployLogs(aiounittest.AsyncTestCase):
    def test_deploy_dir(self):
        deploy_dir = DeploymentDir("user_id", "deploy_id")
        self.assertEqual(deploy_dir.user_id, "user_id")
        self.assertEqual(deploy_dir.user_root, LOG_DIR / "user_id")
        self.assertEqual(deploy_dir.deploy_root, deploy_dir.user_root / "deploy_id")

        log_path = deploy_dir.log_path("stack_id")
        self.assertEqual(log_path, deploy_dir.deploy_root / "stack_id.log")

    def test_update_latest(self):
        deploy_dir = DeploymentDir("user_id", "deploy_id")
        deploy_dir.user_root = MagicMock()
        deploy_dir.deploy_root = MagicMock()
        deploy_dir.deploy_root.name = "deploy_id"

        latest = MagicMock()
        deploy_dir.user_root.__truediv__.return_value = latest
        latest.exists.return_value = True

        deploy_dir.update_latest()

        deploy_dir.user_root.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        latest.exists.assert_called()
        latest.unlink.assert_called_once()
        latest.symlink_to.assert_called_once_with("deploy_id")

    @patch("src.deployer.pulumi.deploy_logs.open")
    def test_on_output(self, mock_open):
        dir = MagicMock()
        path = MagicMock()
        dir.log_path.return_value = path

        file = MagicMock()
        mock_open.return_value = file

        log = DeployLog(dir, "stack_id")

        dir.log_path.assert_called_once_with("stack_id")

        with log.on_output() as on_output:
            on_output("message")

        path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_open.assert_called_once_with(path, "a")
        dir.update_latest.assert_called_once()

        file.write.assert_has_calls(
            [
                call("message\n"),
                call("END\n"),
            ]
        )
        file.flush.assert_called()
        file.close.assert_called_once()

    @patch("src.deployer.pulumi.deploy_logs.open")
    @patch("src.deployer.pulumi.deploy_logs.asyncio.sleep")
    @patch("src.deployer.pulumi.deploy_logs.Observer")
    @patch("src.deployer.pulumi.deploy_logs.asyncio.wait_for")
    async def test_log_tail(self, mock_wait_for, mock_observer, mock_sleep, mock_open):
        observer = MagicMock()
        mock_observer.return_value = observer

        log = MagicMock()
        handler = DeployLogHandler(log)

        # Replace the queue's get so that it doesn't wait indefinitely
        async def get_message():
            return handler.messages.get_nowait()

        handler.messages.get = get_message

        # Convert the QueueEmpty from get_nowait to a TimeoutError
        async def wait_for(x, timeout):
            try:
                return await x
            except QueueEmpty:
                raise TimeoutError()

        mock_wait_for.side_effect = wait_for

        file = MagicMock()
        mock_open.return_value = file

        self.assertEqual(handler, handler.__aiter__())

        log.path.exists.return_value = False

        with self.subTest("File doesn't exist"):
            with self.assertRaises(StopAsyncIteration):
                await handler.__anext__()

            mock_open.assert_not_called()

        log.path.exists.return_value = True

        with self.subTest("File exists with 2 lines"):
            file.readlines.return_value = ["line1\n", "line2\n"]

            self.assertEqual("line1\n", await handler.__anext__())
            self.assertEqual("line2\n", await handler.__anext__())
            self.assertEqual(False, handler.complete)
            mock_observer.assert_called_once()
            observer.schedule.assert_called_once()
            observer.start.assert_called_once()

            with self.assertRaises(TimeoutError):
                await handler.__anext__()

        with self.subTest("Message queue appended after open"):
            handler.messages.put_nowait("line3\n")
            handler.complete = True

            self.assertEqual("line3\n", await handler.__anext__())
            with self.assertRaises(StopAsyncIteration):
                await handler.__anext__()
