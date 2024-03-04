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
from pynamodb.exceptions import DoesNotExist

from src.stack_pack import ConfigValues, StackPack
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.compress import zip_directory_recurse
from src.util.tmp import TempDir
from src.stack_pack.common_stack import CommonStack
from src.util.aws.iam import Policy
from src.stack_pack.models.user_app import AppModel, UserApp
from src.util.logging import logger

class UserPack(Model):

    COMMON_APP_NAME = "common"

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
        base_version = self.apps.get(UserPack.COMMON_APP_NAME, None)
        app: UserApp = None
        if base_version is not None:
            try:
                app = UserApp.get(UserApp.composite_key(self.id, UserPack.COMMON_APP_NAME), base_version)
                app.version += 1
            except DoesNotExist as e:
                logger.info(f"App {UserPack.COMMON_APP_NAME} does not exist for pack id {self.id}. Creating a new one.")
        if app is None:
            app = UserApp(
                app_id=f"{self.id}#{UserPack.COMMON_APP_NAME}",
                version=1,
                created_by=self.created_by,
                created_at=datetime.datetime.now(),
                configuration=config,
            )
        policy = await app.run_app(base_stack, tmp_dir, iac_storage)
        if not dry_run:
            app.save()
            self.apps[UserPack.COMMON_APP_NAME] = app.version
        return policy


    async def run_pack(
        self,
        stack_packs: dict[str, StackPack],
        config: dict[str, ConfigValues],
        tmp_dir: str,
        iac_storage: IacStorage,
        increment_versions: bool = True,
        imports: list[any] = [],
    ) -> Policy:
        """ Run the stack packs with the given configuration and return the combined policy

        Args:
            stack_packs (dict[str, StackPack]): a dictionary of stack packs where the key is the name of the stack pack
            config (dict[str, ConfigValues]): a dictionary of configurations where the key is the name of the stack pack
            tmp_dir (str): the temporary directory to store the files related to the engine execution of the stack pack
            iac_storage (IacStorage): the class to interact with to store the iac
            increment_versions (bool, optional): A flag to enable storing IaC and incrementing the version of the application. If set to false nothing from the run will be saved. Defaults to True.
            imports (list[any], optional): A List of import constraints to apply to all stack packs. Defaults to [].

        Raises:
            ValueError: If the stack pack name is not in the stack_packs

        Returns:
            Policy: The combined policy of all the stack packs
        """
        apps: List[UserApp] = []
        invalid_stacks = []
        for name, config in config.items():
            if name not in stack_packs:
                invalid_stacks.append(name)
                continue
            version = self.apps.get(name, None)
            app: UserApp = None
            if version is not None:
                try:
                    app = UserApp.get(UserApp.composite_key(self.id, name), version)
                    app.version += 1
                except DoesNotExist as e:
                    logger.info(f"App {name} does not exist for pack id {self.id}. Creating a new one.")
            if app is None:
                app = UserApp(
                    app_id=f"{self.id}#{name}",
                    version=1,
                    created_by=self.created_by,
                    created_at=datetime.datetime.now(),
                    configuration=config,
                )
            apps.append(app)

        if len(invalid_stacks) > 0:
            raise ValueError(f"Invalid stack names: {', '.join(invalid_stacks)}")

        # Run the packs in parallel and only store the iac if we are incrementing the version
        tasks = [
            app.run_app(stack_packs[app.get_app_name()], tmp_dir, iac_storage if increment_versions else None, imports)
            for app in apps
        ]
        policies = await asyncio.gather(*tasks)

        if increment_versions:
            for app in apps:
                app.save()
                self.apps[app.get_app_name()] = app.version

        # Combine the policies
        combined_policy = policies[0]
        for policy in policies[1:]:
            combined_policy.combine(policy)

        print("combined")
        print(combined_policy)
        return combined_policy

    def to_user_stack(self):
        stack_packs = {}
        for k, v in self.apps.items():
            try:
                app = UserApp.get(UserApp.composite_key(self.id, k), v)
            except DoesNotExist as e:
                logger.error(f"App {k} does not exist for pack id {self.id}.")
                raise e
            stack_packs[k] = app.to_user_app()
        return UserStack(
            id=self.id,
            owner=self.owner,
            region=self.region,
            assumed_role_arn=self.assumed_role_arn,
            stack_packs=stack_packs,
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
