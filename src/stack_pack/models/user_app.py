import datetime
import os
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pynamodb.attributes import (
    JSONAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UnicodeSetAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.models import Model

from src.deployer.models.deployment import (
    Deployment,
    DeploymentAction,
    DeploymentStatus,
    PulumiStack,
)
from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import (
    RunEngineRequest,
    RunEngineResult,
    run_engine,
)
from src.stack_pack import ConfigValues, StackPack
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
from src.util.compress import zip_directory_recurse
from src.util.logging import logger


class AppLifecycleStatus(Enum):
    NEW = "New"
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


class UserApp(Model):
    class Meta:
        table_name = os.environ.get("USERAPPS_TABLE_NAME", "UserApps")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    # app_id is a composite key around the id of the user pack and the name of the app
    app_id: str = UnicodeAttribute(hash_key=True)
    version: int = NumberAttribute(range_key=True)
    iac_stack_composite_key: str = UnicodeAttribute(null=True)
    created_by: str = UnicodeAttribute()
    created_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )
    outputs: dict[str, str] = JSONAttribute(null=True)
    deployments: list[str] = UnicodeSetAttribute(null=True)
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute(null=True)
    configuration: dict = JSONAttribute()

    def get_deployments(self, attributes: Optional[list[str]] = None):
        # todo: look into why this doesn't work with iac_stack_composite_key
        keys = [
            (
                d,
                UserApp.composite_key(
                    self.get_pack_id(),
                    PulumiStack.sanitize_stack_name(self.get_app_name()),
                ),
            )
            for d in (self.deployments or [])
        ]
        # todo: add pagination
        return Deployment.batch_get(keys, attributes_to_get=attributes)

    def to_user_app(self):
        latest_deployed_version = UserApp.get_latest_deployed_version(self.app_id)
        return AppModel(
            app_id=self.app_id,
            version=self.version,
            created_by=self.created_by,
            created_at=self.created_at,
            configuration=ConfigValues(self.configuration.items()),
            outputs=self.outputs,
            last_deployed_version=(
                latest_deployed_version.version if latest_deployed_version else None
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

    def transition_status(
        self, status: DeploymentStatus, action: DeploymentAction, reason: str
    ):
        new_status = None
        match action:
            case DeploymentAction.DEPLOY:
                match status:
                    case DeploymentStatus.IN_PROGRESS:
                        if self.get_latest_deployed_version(self.app_id) is None:
                            new_status = AppLifecycleStatus.INSTALLING.value
                        else:
                            new_status = AppLifecycleStatus.UPDATING.value
                    case DeploymentStatus.SUCCEEDED:
                        new_status = AppLifecycleStatus.INSTALLED.value
                    case DeploymentStatus.FAILED:
                        if self.status == AppLifecycleStatus.NEW.value:
                            new_status = AppLifecycleStatus.INSTALL_FAILED.value
                        else:
                            new_status = AppLifecycleStatus.UPDATE_FAILED.value
            case DeploymentAction.DESTROY:
                match status:
                    case DeploymentStatus.IN_PROGRESS:
                        new_status = AppLifecycleStatus.UNINSTALLING.value
                    case DeploymentStatus.SUCCEEDED:
                        new_status = AppLifecycleStatus.UNINSTALLED.value
                    case DeploymentStatus.FAILED:
                        new_status = AppLifecycleStatus.UNINSTALL_FAILED.value

        if new_status is None:
            raise ValueError(f"Invalid status transition: {self.status} -> {status}")
        self.update(
            actions=[UserApp.status.set(new_status), UserApp.status_reason.set(reason)]
        )

    def get_app_name(self):
        return self.app_id.split("#")[1]

    def get_pack_id(self):
        return self.app_id.split("#")[0]

    def get_configurations(self) -> ConfigValues:
        return ConfigValues(self.configuration.items())

    def update_configurations(self, configuration: ConfigValues):
        self.update(actions=[UserApp.configuration.set(configuration)])

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
                    name=self.get_pack_id(),
                    tmp_dir=dir,
                )
            )
            print("FILES2", stack_pack.base.files)
            stack_pack.copy_files(self.get_configurations(), Path(dir))
            iac_bytes = zip_directory_recurse(BytesIO(), dir)
            logger.info(f"Writing IAC for {self.app_id} version {self.version}")
            iac_storage.write_iac(
                self.get_pack_id(), self.get_app_name(), self.version, iac_bytes
            )
        return Policy(engine_result.policy)

    @classmethod
    def get_latest_version(cls, app_id: str):
        results = cls.query(
            app_id,
            scan_index_forward=False,  # Sort in descending order
            limit=1,  # Only retrieve the first item
        )
        return next(
            iter(results), None
        )  # Return the first item or None if there are no items

    @classmethod
    def get_latest_deployed_version(cls, app_id: str):
        results = cls.query(
            app_id,
            filter_condition=UserApp.deployments.exists(),  # Only include items where status is not null
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
                else None
            )

    @staticmethod
    def composite_key(pack_id, app_name):
        return f"{pack_id}#{app_name}"


class AppModel(BaseModel):
    app_id: str
    version: int
    iac_stack_composite_key: Optional[str] = None
    created_by: str
    created_at: datetime.datetime
    configuration: ConfigValues = Field(default_factory=dict)
    outputs: Optional[dict[str, str]] = Field(default_factory=dict)
    last_deployed_version: Optional[int] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None
