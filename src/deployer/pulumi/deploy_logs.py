import asyncio
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from watchdog.events import PatternMatchingEventHandler
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
            # Note: this is deliberately being opened and closed on each line
            # because FSEvents on macOS doesn't detect just pure writes (fsync) to the file
            # for some reason.
            # https://github.com/gorakhargosh/watchdog/issues/126#issuecomment-39026219
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

    OBSERVER = Observer()

    def __init__(self, log: DeployLog):
        super().__init__(patterns=[str(log.path)])
        self.interrupted = None
        self.log = log
        self.messages = asyncio.Queue()
        self.complete = False
        self.file = None
        self.sent = 0
        self.watch = None
        # _lock makes sure that the fields used in on_modified are thread safe from access in __anext__
        # ie, that the independent _read_lines calls don't stomp eachother
        self._lock = threading.RLock()

    def close(self, interrupted=True):
        with self._lock:
            if self.watch is not None:
                cleanup_watch(DeployLogHandler.OBSERVER, self.watch)
                self.watch = None
            if self.file is not None:
                self.file.close()
                self.file = None
            self.interrupted = interrupted

    def _read_lines(self):
        """TODO change read lines to just read characters and worry about line breaks on the UI side. This will allow
        Pulumi's '...' to be displayed as it is written to the log file, instead of only once it's finished so that the
        user can see the progress of the deployment as it happens. This change will need to be coordinated all through the
        message queue up to the frontend.
        """
        with self._lock:
            if self.complete:
                return True

            opened_file = False
            if self.file is None:
                if not self.log.path.exists():
                    return False
                self.file = open(self.log.path, "r")
                opened_file = True

            for line in self.file.readlines():
                if line == DeployLog.END_MESSAGE:
                    self.complete = True
                    self.close(interrupted=False)
                    break

                self.messages.put_nowait(line)

            if opened_file and not self.complete:
                self.watch = DeployLogHandler.OBSERVER.schedule(
                    self, str(self.log.path.parent), recursive=False
                )
                with DeployLogHandler.OBSERVER._lock:
                    if not DeployLogHandler.OBSERVER.is_alive():
                        DeployLogHandler.OBSERVER.start()

            return True

    def on_modified(self, event):
        self._read_lines()

    def __aiter__(self):
        return self

    async def __anext__(self):
        # Poll for file creation
        for _ in range(60 * 2):  # wait up to 2 minutes
            if self.interrupted:
                raise StopAsyncIteration
            if self._read_lines():
                break
            await asyncio.sleep(1)
        else:
            logger.warning("Log file %s was never created", self.log.path)
            raise StopAsyncIteration

        if self.interrupted:
            raise StopAsyncIteration

        if self.complete and self.messages.empty():
            logger.debug(
                "Log %s complete (%d messages), stopping", self.log.path, self.sent
            )
            raise StopAsyncIteration

        for _ in range(10):
            try:
                line = await asyncio.wait_for(
                    self.messages.get(),
                    timeout=60,
                )
                if self.interrupted:
                    raise StopAsyncIteration
                self.sent += 1
                return line
            except TimeoutError:
                # manually check to see if the file has been updated
                self._read_lines()
                if not self.messages.empty():
                    logger.debug("Found update from poll, continuing")
                    continue

                if self.complete and self.messages.empty():
                    logger.debug(
                        "Log %s complete (%d messages), stopping",
                        self.log.path,
                        self.sent,
                    )
                    raise StopAsyncIteration

        else:
            logger.warning(
                "No messages in log %s for 10 minutes, stopping", self.log.path
            )
            self.close(interrupted=True)
            raise TimeoutError()


def cleanup_watch(observer, watch):
    """
    Unschedules the watch if there are no more handlers for it. This implementation
    only uses properties on the BaseObserver so it is safe for all implementations.
    """
    with observer._lock:
        if len(observer._handlers[watch]) == 0:
            observer.unschedule(watch)
