import os
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from pulumi import automation as auto

from src.deployer.models.pulumi_stack import PulumiStack
from src.util.compress import zip_directory_recurse
from src.util.logging import logger as log


class AppBuilder:
    def __init__(self, output_dir: Path, state_bucket_name: str):
        self.state_bucket_name = state_bucket_name
        self.output_dir = output_dir

    def prepare_stack(self, pulumi_stack: PulumiStack) -> auto.Stack:
        self.install_npm_deps()
        return self.create_pulumi_stack(pulumi_stack)

    def read_iac_from_disk(self):
        return zip_directory_recurse(BytesIO(), self.output_dir)

    def write_iac_to_disk(self, iac: bytes):
        zip_io = BytesIO(iac)
        with zipfile.ZipFile(zip_io, "r") as zip_file:
            zip_file.extractall(self.output_dir)

    def create_pulumi_stack(self, pulumi_stack: PulumiStack) -> auto.Stack:
        log.info(f"Creating stack for {pulumi_stack.project_name} {pulumi_stack.name}")
        s3_opts = auto.LocalWorkspaceOptions(
            project_settings=auto.ProjectSettings(
                name=PulumiStack.sanitize_stack_name(
                    f"{pulumi_stack.project_name}/{pulumi_stack.name}"
                ),
                runtime="nodejs",
                backend=auto.ProjectBackend(f"s3://{self.state_bucket_name}"),
            ),
            env_vars={
                "PULUMI_CONFIG_PASSPHRASE": "",
                "PULUMI_CONFIG_PASSPHRASE_FILE": "",
            },
        )
        os.environ["PULUMI_DEBUG"] = "true"
        stack = auto.create_or_select_stack(
            stack_name=pulumi_stack.name,
            project_name=pulumi_stack.project_name,
            work_dir=str(self.output_dir),
            opts=s3_opts if self.state_bucket_name else None,
        )
        log.info(
            f"Successfully created stack for {pulumi_stack.project_name} {pulumi_stack.name}"
        )
        return stack

    def configure_aws(
        self,
        stack: auto.Stack,
        region: str,
        role_arn: str,
        external_id: Optional[str] = None,
    ):
        stack.set_config("aws:region", auto.ConfigValue(region))
        stack.set_config(
            "aws:assumeRole.roleArn", auto.ConfigValue(role_arn), path=True
        )
        if external_id:
            stack.set_config(
                "aws:assumeRole.externalId", auto.ConfigValue(external_id), path=True
            )

    def install_npm_deps(self):
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            ["npm", "install", "--prefix", self.output_dir],
            stdout=subprocess.DEVNULL,
        )
        result.check_returncode()
