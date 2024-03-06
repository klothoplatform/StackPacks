import datetime
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pynamodb.attributes import (
    JSONAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.models import Model

from src.deployer.models.deployment import PulumiStack
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


class UserApp(Model):
    class Meta:
        table_name = "UserApps"
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)

    # app_id is a composite key around the id of the user pack and the name of the app
    app_id: str = UnicodeAttribute(hash_key=True)
    version: int = NumberAttribute(range_key=True)
    iac_stack_composite_key: str = UnicodeAttribute(null=True)
    created_by: str = UnicodeAttribute()
    created_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )
    status: str = UnicodeAttribute(null=True)
    status_reason: str = UnicodeAttribute(null=True)
    configuration: dict = JSONAttribute()

    def to_user_app(self):
        pulumi_stack = None
        if self.iac_stack_composite_key:
            hash_key, range_key = PulumiStack.split_composite_key(
                self.iac_stack_composite_key
            )
            pulumi_stack = PulumiStack.get(hash_key=hash_key, range_key=range_key)
        latest_deployed_version = UserApp.get_latest_version_with_status(self.app_id)
        return AppModel(
            app_id=self.app_id,
            version=self.version,
            created_by=self.created_by,
            created_at=self.created_at,
            configuration=ConfigValues(self.configuration.items()),
            last_deployed_version=(
                latest_deployed_version.version if latest_deployed_version else None
            ),
            status=pulumi_stack.status if pulumi_stack else None,
            status_reason=pulumi_stack.status_reason if pulumi_stack else None,
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
        imports: list[any] = [],
    ) -> Policy:
        constraints = stack_pack.to_constraints(self.get_configurations())
        constraints.extend(imports)
        engine_result: RunEngineResult = await run_engine(
            RunEngineRequest(
                constraints=constraints,
                tmp_dir=dir,
            )
        )
        if iac_storage:
            await export_iac(
                ExportIacRequest(
                    input_graph=engine_result.resources_yaml,
                    name="stack",
                    tmp_dir=dir,
                )
            )
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
    def get_latest_version_with_status(cls, app_id: str):
        results = cls.query(
            app_id,
            filter_condition=UserApp.status.exists(),  # Only include items where status is not null
            scan_index_forward=False,  # Sort in descending order
            limit=1,  # Only retrieve the first item
        )
        return next(
            iter(results), None
        )  # Return the first item or None if there are no items

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
    last_deployed_version: Optional[int] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None
