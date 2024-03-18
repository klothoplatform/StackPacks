import asyncio
import os
from contextlib import contextmanager
from pathlib import Path

from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler
from watchdog.observers import Observer

from src.util.logging import logger

LOG_DIR = Path(os.getenv("DEPLOY_LOG_DIR", "deployments"))
PRINT_LOGS = os.getenv("PRINT_LOGS", False)


class DeploymentDir:
    """DeploymentDir is a class that represents a directory where deployment logs are stored for a given user.
    It's mostly a convenience class to encapsulate the logic of where logs are stored and how to access them.
    """

    def __init__(self, user_id: str, deploy_id: str):
        self.user_id = user_id
        self.user_root = LOG_DIR / user_id
        self.deploy_root = self.user_root / deploy_id

    def log_path(self, stack_id: str):
        return self.deploy_root / f"{stack_id}.log"

    def get_log(self, stack_id: str):
        return DeployLog(
            self,
            stack_id,
        )

    def update_latest(self):
        self.user_root.mkdir(parents=True, exist_ok=True)

        latest = self.user_root / "latest"

        logger.info(
            "Linking %s -> %s (%s)", latest, self.deploy_root.name, latest.exists()
        )
        if latest.exists():
            latest.unlink()
        latest.symlink_to(self.deploy_root.name)


class DeployLog:
    # sentinel value to indicate end of log, more robust than
    # passing messages between writer and reader in memory.
    # This allows the reader to properly detect completed deployments
    # even across restarts.
    END_MESSAGE = "END\n"

    def __init__(self, dir: DeploymentDir, stack_id: str):
        self.dir = dir
        self.stack_id = stack_id
        self.path = dir.log_path(stack_id)
        self.deploy_handler = None

    @contextmanager
    def on_output(self):
        """on_output is a context manager that opens the log file for writing and returns a function
        that can be used in pulumi automation calls' on_output parameter to write to the log file.
        On exit, it writes the END_MESSAGE to the log file to signal to any readers that the log file is complete.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.dir.update_latest()

        def on_output(s: str):
            if PRINT_LOGS:
                print(s)
            with open(self.path, "a") as writer:
                writer.write(s + "\n")

        try:
            yield on_output
        finally:
            with open(self.path, "a") as writer:
                writer.write(DeployLog.END_MESSAGE)

    def tail(self):
        if self.deploy_handler is None:
            self.deploy_handler = DeployLogHandler(self)
        return self.deploy_handler

    def close(self):
        if self.deploy_handler:
            self.deploy_handler.close()


class DeployLogHandler(PatternMatchingEventHandler):
    """DeployLogHandler is used for communication between the watchdog FileSystemEventHandler and the StreamingResponse
    using a Queue to pass messages between the two.
    """

    def __init__(self, log: DeployLog):
        super().__init__(patterns=[str(log.path)])
        self.interrupted = None
        self.observer = None
        self.log = log
        self.messages = asyncio.Queue()
        self.complete = False
        self.file = None
        self.sent = 0

    def close(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        if self.file:
            self.file.close()
        self.interrupted = True

    def on_modified(self, event):
        line_count = 0
        for line in self.file.readlines():
            line_count += 1
            if line.strip() == "END":
                self.complete = True
                self.observer.stop()
                break
            else:
                self.messages.put_nowait(line)

    def __aiter__(self):
        return self

    def setup_file(self):
        self.file = open(self.log.path, "r")
        for line in self.file.readlines():
            if line == DeployLog.END_MESSAGE:
                self.complete = True
                logger.info(
                    "Log %s already complete with %d lines",
                    self.log.path,
                    self.messages.qsize(),
                )
                break
            else:
                self.messages.put_nowait(line)

        if not self.complete:
            self.observer = Observer()
            self.observer.schedule(self, str(self.log.path.parent), recursive=False)
            self.observer.start()

    async def __anext__(self):
        if self.interrupted:
            raise StopAsyncIteration
        if self.file is None:
            # Poll for file creation
            for attempt in range(60 * 2):  # wait up to 2 minutes
                if self.interrupted:
                    raise StopAsyncIteration
                if self.log.path.exists():
                    break
                await asyncio.sleep(1)
            if not self.log.path.exists():
                logger.warning("Log file %s was never created", self.log.path)
                raise StopAsyncIteration

            if self.interrupted:
                raise StopAsyncIteration
            self.setup_file()

        if self.complete and self.messages.empty():
            logger.debug(
                "Log %s complete (%d messages), stopping", self.log.path, self.sent
            )
            raise StopAsyncIteration

        try:
            line = await asyncio.wait_for(
                self.messages.get(),
                timeout=60 * 10,
            )
            if self.interrupted:
                raise StopAsyncIteration
            self.sent += 1
            return line
        except TimeoutError:
            if self.complete and self.messages.empty():
                logger.debug(
                    "Log %s complete (%d messages), stopping", self.log.path, self.sent
                )
                raise StopAsyncIteration
            raise
