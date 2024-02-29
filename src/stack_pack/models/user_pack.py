from io import BytesIO
import os
import re
from tempfile import TemporaryDirectory
from pydantic import BaseModel, Field
import datetime
from enum import Enum
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    JSONAttribute,
    UTCDateTimeAttribute,
)
from src.engine_service.engine_commands.export_iac import ExportIacRequest, export_iac
from src.engine_service.engine_commands.run import RunEngineRequest, RunEngineResult, run_engine

from src.stack_pack import StackConfig, StackPack, ConfigValues
from src.deployer.models.deployment import PulumiStack
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.compress import zip_directory_recurse


class UserPack(Model):
    class Meta:
        table_name = "UserPacks"
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)

    id: str = UnicodeAttribute(hash_key=True)
    owner: str = UnicodeAttribute(range_key=True)
    region: str = UnicodeAttribute(null=True)
    assumed_role_arn: str = UnicodeAttribute(null=True)
    # Configuration is a dictionary where the keys are the oss package
    # and the value is another dictionary of the key value configurations for that oss package
    configuration: dict = JSONAttribute()
    iac_stack_composite_key: str = UnicodeAttribute(null=True)
    created_by: str = UnicodeAttribute()
    created_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )
    
    def get_configurations(self) -> dict[str, ConfigValues]:
        return {
            k: ConfigValues(v) for k, v in self.configuration.items()
        }

    def update_configurations(self, configuration: dict):
        self.update(actions=[UserPack.configuration.set(configuration)])
        
    def to_user_stack(self):
        pulumi_stack = None
        if self.iac_stack_composite_key:
            hash_key, range_key = PulumiStack.split_composite_key(self.iac_stack_composite_key)
            pulumi_stack = PulumiStack.get(hash_key=hash_key, range_key=range_key)
        return UserStack(
            id=self.id,
            owner=self.owner,
            region=self.region,
            assumed_role_arn=self.assumed_role_arn,
            configuration={
                k: ConfigValues(v) for k, v in self.configuration.items()    
            },
            status=pulumi_stack.status if pulumi_stack else None,
            status_reason=pulumi_stack.status_reason if pulumi_stack else None,
            created_by=self.created_by,
            created_at=self.created_at,
        )
        
    async def run_pack(self, stack_packs: dict[str, StackPack], iac_storage: IacStorage) -> str:
        constraints = []
        invalid_stacks = []
        for stack_name, config in self.get_configurations().items():
            if stack_name not in stack_packs:
                invalid_stacks.append(stack_name)
                continue
            stack_pack = stack_packs[stack_name]
            constraints.extend(stack_pack.to_constraints(config))
            
        if len(invalid_stacks) > 0:
            raise ValueError(f"Invalid stack names: {invalid_stacks}")
            
        engine_result: RunEngineResult = await run_engine(
            RunEngineRequest(
                constraints=constraints,
            )
        )
        with TemporaryDirectory() as tmp_dir:
            await export_iac(
                ExportIacRequest(
                    input_graph=engine_result.resources_yaml,
                    name="stack",
                    tmp_dir=tmp_dir,
                )
            )
            
            for stack_name, config in self.get_configurations().items():
                stack_pack = stack_packs[stack_name]
                stack_pack.copy_files(config, tmp_dir)
            iac_bytes = zip_directory_recurse(BytesIO(), tmp_dir)
            iac_storage.write_iac(self, iac_bytes)
        return engine_result.policy

class UserStack(BaseModel):
    id: str
    owner: str
    region: str = None
    assumed_role_arn: str = None
    configuration: dict[str, ConfigValues] = Field(default_factory=dict)
    status: str = None
    status_reason: str = None
    created_by: str
    created_at: datetime.datetime