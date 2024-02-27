import subprocess
import os
from pulumi import automation as auto
import shutil
import tempfile
import io
import zipfile
from src.deployer.models.deployment import PulumiStack
from src.util.aws.sts import assume_role
from src.util.logging import logger as log


class AppBuilder:
    def __init__(self, sts_client):
        self.sts_client = sts_client
        self.output_dir = tempfile.mkdtemp()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.output_dir)

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
        creds, user = assume_role(self.sts_client, role_arn)
        stack.set_config("aws:accessKey", auto.ConfigValue(creds.AccessKeyId))
        stack.set_config("aws:secretKey", auto.ConfigValue(creds.SecretAccessKey))
        stack.set_config("aws:token", auto.ConfigValue(creds.SessionToken))
        stack.set_config("aws:region", auto.ConfigValue(region))

    def install_npm_deps(self):
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            ["npm", "install", "--prefix", self.output_dir],
            stdout=open(os.devnull, "wb"),
        )
        result.check_returncode()
