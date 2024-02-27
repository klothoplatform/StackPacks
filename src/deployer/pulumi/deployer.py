from multiprocessing import Queue
import jsons
from pulumi import automation as auto
from src.deployer.models.deployment import DeploymentStatus
from src.util.logging import logger


class AppDeployer:
    def __init__(self, stack: auto.Stack):
        self.stack = stack

    async def deploy(self, q: Queue) -> tuple[DeploymentStatus, str | None]:
        try:
            preview_result = self.stack.preview()
            logger.info(f"Preview result: {preview_result}")
        except Exception as e:
            logger.error(f"Failed to preview stack", exc_info=True)
            return DeploymentStatus.FAILED, e.__str__()
        try:
            result: auto.UpResult = self.stack.up(on_output=print)
            logger.info(f"Deployed stack, {self.stack.name}, successfully.")
            return DeploymentStatus.SUCCEEDED, jsons.dump(result.outputs.items())
        except Exception as e:
            logger.error(
                f"Deployment of stack, {self.stack.name}, failed.", exc_info=True
            )
            logger.info(f"Refreshing stack {self.stack.name}")
            self.stack.refresh()
            return DeploymentStatus.FAILED, None

    async def destroy_and_remove_stack(
        self, q: Queue
    ) -> tuple[DeploymentStatus, str | None]:
        try:
            self.stack.destroy(on_output=print)
            logger.info(f"Removing stack {self.stack.name}")
            self.stack.workspace.remove_stack(self.stack.name)
            return DeploymentStatus.SUCCEEDED, None
        except Exception as e:
            logger.error(e)
            logger.info(f"Refreshing stack {self.stack.name}")
            self.stack.refresh()
            return DeploymentStatus.FAILED, None
