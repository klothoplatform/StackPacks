import asyncio
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Optional, Tuple, List, Set
from pydantic import BaseModel, Field
import datetime
from enum import Enum
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    UTCDateTimeAttribute,
    JSONAttribute,
)

from src.stack_pack import ConfigValues, StackPack
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.compress import zip_directory_recurse
from src.util.tmp import TempDir
from stack_pack.common_stack import CommonStack
from src.util.aws.iam import Policy
from src.stack_pack.models.user_app import AppModel, UserApp


class UserPack(Model):

    BASE_APP_NAME = "base"

    class Meta:
        table_name = "UserPacks"
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)

    id: str = UnicodeAttribute(hash_key=True)
    owner: str = UnicodeAttribute()
    region: str = UnicodeAttribute(null=True)
    assumed_role_arn: str = UnicodeAttribute(null=True)
    # Configuration is a dictionary where the keys are the oss package
    # and the value is another dictionary of the key value configurations for that oss package
    apps: dict[str, int] = JSONAttribute()
    created_by: str = UnicodeAttribute()
    created_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )

    async def run_base(
        self,
        stack_packs: List[StackPack],
        config: ConfigValues,
        tmp_dir: str,
        iac_storage: IacStorage,
        dry_run: bool = True,
    ) -> Policy:
        base_stack = CommonStack(stack_packs)
        base_version = self.apps.get("base", None)
        app: UserApp
        if base_version is not None:
            app = UserApp.get(UserApp.composite_key(self.id, "base"), base_version)
        else:
            app = UserApp(
                app_id=f"{self.id}#base",
                version=0,
                created_by=self.created_by,
                created_at=datetime.datetime.now(),
                configuration=config,
            )
        policy = await app.run_app(base_stack, tmp_dir, iac_storage, dry_run)
        if not dry_run:
            app.version += 1
            app.save()
            self.apps["base"] = app.version
        return policy

    async def run_pack(
        self,
        stack_packs: dict[str, StackPack],
        config: dict[str, ConfigValues],
        tmp_dir: str,
        iac_storage: IacStorage | None = None,
        increment_versions: bool = True,
        imports: list[any] = [],
    ) -> Policy:

        apps: List[UserApp] = []
        invalid_stacks = []
        for name, config in config.items():
            if name not in stack_packs:
                invalid_stacks.append(name)
                continue
            version = self.apps.get(name, None)
            app: UserApp
            if version is not None:
                app = UserApp.get(UserApp.composite_key(self.id, name), version)
            else:
                app = UserApp(
                    app_id=f"{self.id}#{name}",
                    version=0,
                    created_by=self.created_by,
                    created_at=datetime.datetime.now(),
                    configuration=config,
                )
            apps.append(app)

        if len(invalid_stacks) > 0:
            raise ValueError(f"Invalid stack names: {', '.join(invalid_stacks)}")

        # Run the packs in parallel
        tasks = [
            app.run_app(stack_packs[app.get_app_name()], tmp_dir, iac_storage, imports)
            for app in apps
        ]
        policies = await asyncio.gather(*tasks)

        if increment_versions:
            for app in apps:
                app.version += 1
                app.save()
                self.apps[app.get_app_name()] = app.version

        # Combine the policies
        combined_policy = Policy()  # Initialize an empty policy
        for policy in policies:
            combined_policy.combine(policy)

        return combined_policy

    def to_user_stack(self):
        return UserStack(
            id=self.id,
            owner=self.owner,
            region=self.region,
            assumed_role_arn=self.assumed_role_arn,
            stack_packs={k: v.to_user_app() for k, v in self.apps.items()},
            created_by=self.created_by,
            created_at=self.created_at,
        )

class UserStack(BaseModel):
    id: str
    owner: str
    region: Optional[str] = None
    assumed_role_arn: Optional[str] = None
    stack_packs: dict[str, AppModel] = Field(default_factory=dict)
    created_by: str
    created_at: datetime.datetime
