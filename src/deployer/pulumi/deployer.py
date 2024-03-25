from typing import Tuple

from pulumi import automation as auto

from src.deployer.models.deployment import DeploymentStatus
from src.deployer.pulumi.deploy_logs import DeploymentDir
from src.util.logging import logger


class AppDeployer:
    def __init__(self, stack: auto.Stack, deploy_dir: DeploymentDir):
        self.stack = stack
        self.deploy_dir = deploy_dir
        self.deploy_log = deploy_dir.get_log(stack.name)
        self.deploy_dir.update_latest()

    async def deploy(self) -> Tuple[DeploymentStatus, str]:
        with self.deploy_log.on_output() as on_output:
            try:
                self.stack.refresh(on_output=on_output, color="always")
                preview_result = self.stack.preview(on_output=on_output, color="always")
            except Exception as e:
                logger.error(f"Failed to preview stack", exc_info=True)
                return DeploymentStatus.FAILED, str(e)
            try:
                self.stack.up(on_output=on_output, color="always")
                logger.info(f"Deployed stack, {self.stack.name}, successfully.")
                return DeploymentStatus.SUCCEEDED, "Deployment succeeded."
            except Exception as e:
                logger.error(
                    f"Deployment of stack, {self.stack.name}, failed.", exc_info=True
                )
                logger.info(f"Refreshing stack {self.stack.name}")
                self.stack.refresh(on_output=on_output, color="always")
                return DeploymentStatus.FAILED, str(e)

    async def destroy_and_remove_stack(self) -> Tuple[DeploymentStatus, str]:
        with self.deploy_log.on_output() as on_output:
            try:
                self.stack.refresh(on_output=on_output, color="always")
                self.stack.destroy(on_output=on_output, color="always")
                logger.info(f"Removing stack {self.stack.name}")
                self.stack.workspace.remove_stack(self.stack.name)
                return DeploymentStatus.SUCCEEDED, "Stack removed successfully."
            except Exception as e:
                logger.error(
                    f"Destroy of stack, {self.stack.name}, failed.", exc_info=True
                )
                logger.info(f"Refreshing stack {self.stack.name}")
                self.stack.refresh(on_output=on_output, color="always")
                return DeploymentStatus.FAILED, str(e)
