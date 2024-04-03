import os
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pynamodb.attributes import (
    JSONAttribute,
    UnicodeAttribute,
    UnicodeSetAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.models import Model

from src.deployer.models.workflow_job import WorkflowJobStatus, WorkflowJobType
from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import (
    RunEngineRequest,
    RunEngineResult,
    run_engine,
)
from src.project import ConfigValues, StackPack
from src.project.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
from src.util.compress import zip_directory_recurse
from src.util.logging import logger


class AppLifecycleStatus(Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    INSTALLING = "INSTALLING"
    INSTALLED = "INSTALLED"
    UPDATING = "UPDATING"
    INSTALL_FAILED = "INSTALL_FAILED"
    UPDATE_FAILED = "UPDATE_FAILED"
    UNINSTALLING = "UNINSTALLING"
    UNINSTALL_FAILED = "UNINSTALL_FAILED"
    UNINSTALLED = "UNINSTALLED"
    UNKNOWN = "UNKNOWN"


class AppDeployment(Model):
    class Meta:
        table_name = os.environ.get("APP_DEPLOYMENTS_TABLE_NAME", "AppDeployments")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    project_id: str = UnicodeAttribute(hash_key=True)
    # composite key: app_id#version
    range_key: str = UnicodeAttribute(range_key=True)
    iac_stack_composite_key: str = UnicodeAttribute(null=True)
    created_by: str = UnicodeAttribute()
    created_at: datetime = UTCDateTimeAttribute(default=datetime.utcnow)
    outputs: dict[str, str] = JSONAttribute(null=True)
    deployments: list[str] = UnicodeSetAttribute(null=True)
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute(null=True)
    configuration: dict = JSONAttribute()
    display_name: str = UnicodeAttribute(null=True)

    def app_id(self):
        return self.range_key.split("#")[0]

    def version(self):
        return int(self.range_key.split("#")[1]) if "#" in self.range_key else None

    def to_view_model(self):
        latest_deployed_version = AppDeployment.get_latest_deployed_version(
            self.project_id, self.app_id()
        )
        return AppDeploymentView(
            app_id=self.app_id(),
            version=self.version(),
            created_by=self.created_by,
            created_at=self.created_at,
            configuration=ConfigValues(self.configuration.items()),
            display_name=self.display_name if self.display_name else self.app_id(),
            outputs=self.outputs,
            last_deployed_version=(
                latest_deployed_version.version() if latest_deployed_version else None
            ),
            status=self.status if self.status else latest_deployed_version.status,
            status_reason=(
                self.status_reason
                if self.status_reason
                else (
                    latest_deployed_version.status_reason
                    if latest_deployed_version
                    else None
                )
            ),
        )

    def __eq__(self, other):
        return (
            self.project_id == other.project_id
            and self.range_key == other.range_key
            and self.iac_stack_composite_key == other.iac_stack_composite_key
            and self.created_by == other.created_by
            and self.created_at == other.created_at
            and self.outputs == other.outputs
            and self.deployments == other.deployments
            and self.status == other.status
            and self.status_reason == other.status_reason
            and self.configuration == other.configuration
            and self.display_name == other.display_name
        )

    def transition_status(
        self, status: WorkflowJobStatus, action: WorkflowJobType, reason: str
    ):
        new_status = None
        match action:
            case WorkflowJobType.DEPLOY:
                match status:
                    case WorkflowJobStatus.IN_PROGRESS:
                        if (
                            self.get_latest_deployed_version(
                                project_id=self.project_id, app_id=self.app_id()
                            )
                            is None
                        ):
                            new_status = AppLifecycleStatus.INSTALLING.value
                        else:
                            new_status = AppLifecycleStatus.UPDATING.value
                    case WorkflowJobStatus.SUCCEEDED:
                        new_status = AppLifecycleStatus.INSTALLED.value
                    case WorkflowJobStatus.FAILED:
                        if self.status == AppLifecycleStatus.NEW.value:
                            new_status = AppLifecycleStatus.INSTALL_FAILED.value
                        else:
                            new_status = AppLifecycleStatus.UPDATE_FAILED.value
            case WorkflowJobType.DESTROY:
                match status:
                    case WorkflowJobStatus.IN_PROGRESS:
                        new_status = AppLifecycleStatus.UNINSTALLING.value
                    case WorkflowJobStatus.SUCCEEDED:
                        new_status = AppLifecycleStatus.UNINSTALLED.value
                    case WorkflowJobStatus.FAILED:
                        new_status = AppLifecycleStatus.UNINSTALL_FAILED.value

        if new_status is None:
            raise ValueError(f"Invalid status transition: {self.status} -> {status}")
        self.update(
            actions=[
                AppDeployment.status.set(new_status),
                AppDeployment.status_reason.set(reason),
            ]
        )

    def get_app_id(self):
        return self.app_id()

    def get_project_id(self):
        return self.project_id

    def get_configurations(self) -> ConfigValues:
        return ConfigValues(self.configuration.items())

    def update_configurations(self, configuration: ConfigValues):
        self.update(actions=[AppDeployment.configuration.set(configuration)])

    async def run_app(
        self,
        stack_pack: StackPack,
        dir: str,
        iac_storage: IacStorage | None,
        binary_storage: BinaryStorage | None,
        imports: list[any] = [],
    ) -> Policy:
        constraints = stack_pack.to_constraints(self.get_configurations())
        constraints.extend(imports)
        binary_storage.ensure_binary(Binary.ENGINE)
        engine_result: RunEngineResult = await run_engine(
            RunEngineRequest(
                constraints=constraints,
                tmp_dir=dir,
            )
        )
        if iac_storage:
            binary_storage.ensure_binary(Binary.IAC)
            await export_iac(
                ExportIacRequest(
                    input_graph=engine_result.resources_yaml,
                    name=self.project_id,
                    tmp_dir=dir,
                )
            )
            stack_pack.copy_files(self.get_configurations(), Path(dir))
            iac_bytes = zip_directory_recurse(BytesIO(), dir)
            logger.info(f"Writing IAC for {self.app_id()} version {self.version()}")
            iac_storage.write_iac(
                self.get_project_id(), self.app_id(), self.version(), iac_bytes
            )
        return Policy(engine_result.policy)

    @classmethod
    def get_latest_version(
        cls, project_id: str, app_id: str
    ) -> Optional["AppDeployment"]:
        results = cls.query(
            project_id,
            range_key_condition=cls.range_key.startswith(f"{app_id}#"),
            scan_index_forward=False,  # Sort in descending order
            limit=1,  # Only retrieve the first item
        )
        return next(
            iter(results), None
        )  # Return the first item or None if there are no items

    @classmethod
    def get_latest_deployed_version(
        cls, project_id: str, app_id: str
    ) -> Optional["AppDeployment"]:
        results = cls.query(
            project_id,
            AppDeployment.range_key.startswith(f"{app_id}#"),
            filter_condition=AppDeployment.deployments.exists(),  # Only include items where status is not null
            scan_index_forward=False,  # Sort in descending order
            limit=1,  # Only retrieve the first item
        )
        result = next(
            iter(results), None
        )  # Return the first item or None if there are no items
        if result:
            return (
                result
                if result.status is not AppLifecycleStatus.UNINSTALLED.value
                or result.status is not AppLifecycleStatus.NEW.value
                else None
            )

    @staticmethod
    def compose_range_key(app_id, version):
        return f"{app_id}#{version:08}"


class AppDeploymentView(BaseModel):
    app_id: str
    version: int
    iac_stack_composite_key: Optional[str] = None
    created_by: str
    created_at: datetime
    configuration: ConfigValues = Field(default_factory=dict)
    display_name: Optional[str] = None
    outputs: Optional[dict[str, str]] = Field(default_factory=dict)
    last_deployed_version: Optional[int] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None
