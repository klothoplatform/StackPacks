import asyncio
import os
from contextlib import contextmanager
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.util.logging import logger

LOG_DIR = Path(os.getenv("DEPLOY_LOG_DIR", "deployments"))


class DeploymentDir:
    """DeploymentDir is a class that represents a directory where deployment logs are stored for a given user.
    It's mostly a convenience class to encapsulate the logic of where logs are stored and how to access them.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        self.log_root = LOG_DIR / user_id

    def log_path(self, stack_id: str, log_type: str, deploy_id: str):
        return self.log_root / stack_id / f"{log_type}_{deploy_id}.log"

    def get_log(self, stack_id, log_type, deploy_id):
        return DeployLog(
            self,
            stack_id,
            log_type,
            deploy_id,
        )


class DeployLog:
    # sentinel value to indicate end of log, more robust than
    # passing messages between writer and reader in memory.
    # This allows the reader to properly detect completed deployments
    # even across restarts.
    END_MESSAGE = "END\n"

    def __init__(self, dir: DeploymentDir, stack_id, log_type, deploy_id):
        self.dir = dir
        self.path = dir.log_path(stack_id, log_type, deploy_id)
        self.stack_id = stack_id
        self.log_type = log_type
        self.deploy_id = deploy_id

    @contextmanager
    def on_output(self):
        """on_output is a context manager that opens the log file for writing and returns a function
        that can be used in pulumi automation calls' on_output parameter to write to the log file.
        On exit, it writes the END_MESSAGE to the log file to signal to any readers that the log file is complete.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        writer = open(self.path, "a")

        latest = self.dir.log_path(self.stack_id, self.log_type, "latest")
        if latest.exists():
            latest.unlink()
        latest.symlink_to(self.path.name)

        def on_output(s: str):
            writer.write(s + "\n")
            writer.flush()

        try:
            yield on_output
        finally:
            writer.write(DeployLog.END_MESSAGE)
            writer.close()

    def tail(self):
        return DeployLogHandler(self)

    async def tail_wait_created(self):
        while not self.path.exists():
            await asyncio.sleep(1)
        return DeployLogHandler(self)


class DeployLogHandler(FileSystemEventHandler):
    """DeployLogHandler is used for communcation between the watchdog FileSystemEventHandler and the StreamingResponse
    using a Queue to pass messages between the two.
    """

    def __init__(self, log: DeployLog):
        self.log = log
        self.messages = asyncio.Queue()
        self.complete = False

        self.reader = open(self.log.path, "r")
        for line in self.reader.readlines():
            if line == DeployLog.END_MESSAGE:
                self.complete = True
                logger.info("Log already complete")
                break
            else:
                self.messages.put_nowait(line)

        if not self.complete:
            self.observer = Observer()
            self.observer.schedule(self, str(log.path), recursive=False)
            self.observer.start()

    def on_any_event(self, event):
        line_count = 0
        for line in self.reader.readlines():
            line_count += 1
            if line.strip() == "END":
                self.complete = True
                self.observer.stop()
                break
            else:
                self.messages.put_nowait(line)
        logger.info("Read %d lines from log", line_count)

    def __aiter__(self):
        return self

    async def __anext__(self):
        for attempt in range(12):  # wait up to 1 minute (12*5 seconds)
            if self.complete and self.messages.empty():
                raise StopAsyncIteration

            try:
                line = await asyncio.wait_for(
                    self.messages.get(),
                    timeout=5,
                )
                return line
            except TimeoutError:
                logger.info("Timed out waiting for logs on iteration %d", attempt)
                pass
