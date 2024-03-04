import subprocess
import os
from pulumi import automation as auto
import io
import zipfile

from src.deployer.models.deployment import PulumiStack
from src.util.logging import logger as log
from src.util.tmp import TempDir


class AppBuilder:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def prepare_stack(self, iac: bytes, pulumi_stack: PulumiStack) -> auto.Stack:
        self.create_output_dir(iac)
        self.install_npm_deps()
        return self.create_pulumi_stack(pulumi_stack)

    def create_output_dir(self, iac: bytes):
        # Create a BytesIO object from the bytes
        zip_io = io.BytesIO(iac)
        # Open the BytesIO object with zipfile.ZipFile
        with zipfile.ZipFile(zip_io, "r") as zip_file:
            # Extract all files and directories from the zip file
            zip_file.extractall(self.output_dir)

    def create_pulumi_stack(self, pulumi_stack: PulumiStack) -> auto.Stack:
        os.environ["PULUMI_DEBUG"] = "true"
        stack = auto.create_or_select_stack(
            stack_name=pulumi_stack.name,
            project_name=pulumi_stack.project_name,
            work_dir=self.output_dir,
        )
        log.info(
            f"Successfully created stack for {pulumi_stack.project_name} {pulumi_stack.name}"
        )
        return stack

    def configure_aws(self, stack: auto.Stack, role_arn: str, region: str):
        stack.set_config("aws:region", auto.ConfigValue(region))
        stack.set_config(
            "roleArn", auto.ConfigValue(role_arn), path="aws:assumeRole.roleArn"
        )

    def install_npm_deps(self):
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            ["npm", "install", "--prefix", self.output_dir],
            stdout=subprocess.DEVNULL,
        )
        result.check_returncode()
