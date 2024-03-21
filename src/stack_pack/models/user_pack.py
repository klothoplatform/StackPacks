import asyncio
import datetime
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pynamodb.attributes import (
    BooleanAttribute,
    JSONAttribute,
    ListAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.exceptions import DoesNotExist
from pynamodb.models import Model

from src.engine_service.binaries.fetcher import BinaryStorage
from src.stack_pack import ConfigValues, StackPack
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.models.user_app import AppLifecycleStatus, AppModel, UserApp
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
from src.util.logging import logger


class UserPack(Model):

    COMMON_APP_NAME = "common"

    class Meta:
        table_name = os.environ.get("USERPACKS_TABLE_NAME", "UserPacks")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    id: str = UnicodeAttribute(hash_key=True)
    owner: str = UnicodeAttribute()
    region: str = UnicodeAttribute(null=True)
    assumed_role_arn: str = UnicodeAttribute(null=True)
    features: List[str] = ListAttribute(null=True)
    apps: dict[str, int] = JSONAttribute()
    created_by: str = UnicodeAttribute()
    created_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )
    tear_down_in_progress: bool = BooleanAttribute(default=False)

    async def run_base(
        self,
        stack_packs: List[StackPack],
        config: ConfigValues,
        iac_storage: IacStorage,
        binary_storage: BinaryStorage,
        tmp_dir: str,
        dry_run: bool = False,
    ) -> Policy:
        base_stack = CommonStack(stack_packs, self.features)
        base_version = self.apps.get(UserPack.COMMON_APP_NAME, None)
        app: UserApp = None
        if base_version is not None:
            try:
                app = UserApp.get(
                    UserApp.composite_key(self.id, UserPack.COMMON_APP_NAME),
                    base_version,
                )
                # Only increment version if there has been an attempted deploy on the current version
                latest_version = UserApp.get_latest_deployed_version(app.app_id)
                if latest_version is not None and latest_version.version >= app.version:
                    app.version = latest_version.version + 1
                    app.deployments = {}
            except DoesNotExist as e:
                logger.info(
                    f"App {UserPack.COMMON_APP_NAME} does not exist for pack id {self.id}. Creating a new one."
                )
        if app is None:
            app = UserApp(
                # This has to be a composite key so we can correlate the app with the pack
                app_id=UserApp.composite_key(self.id, UserPack.COMMON_APP_NAME),
                version=1,
                created_by=self.created_by,
                created_at=datetime.datetime.now(),
                configuration=config,
                status=AppLifecycleStatus.NEW.value,
            )
        health_endpoint_url = os.environ.get(
            "HEALTH_ENDPOINT_URL", "http://localhost:3000"
        )
        app.configuration.update(
            {"PackId": self.id, "HealthEndpointUrl": health_endpoint_url}
        )

        # Run the packs in parallel and only store the iac if we are incrementing the version
        subdir = Path(tmp_dir) / app.get_app_name()
        subdir.mkdir(exist_ok=True)
        policy = await app.run_app(
            base_stack, str(subdir.absolute()), iac_storage, binary_storage
        )

        if not dry_run:
            app.save()
            self.apps[UserPack.COMMON_APP_NAME] = app.version
        return policy

    async def run_pack(
        self,
        stack_packs: dict[str, StackPack],
        config: dict[str, ConfigValues],
        tmp_dir: str,
        iac_storage: IacStorage = None,
        binary_storage: BinaryStorage = None,
        increment_versions: bool = True,
        imports: list[any] = [],
    ) -> Policy:
        """Run the stack packs with the given configuration and return the combined policy

        Args:
            stack_packs (dict[str, StackPack]): a dictionary of stack packs where the key is the name of the stack pack
            config (dict[str, ConfigValues]): a dictionary of configurations where the key is the name of the stack pack
            tmp_dir (str): the temporary directory to store the files related to the engine execution of the stack pack
            iac_storage (IacStorage): the class to interact with to store the iac. If None the iac will not be stored.
            increment_versions (bool, optional): A flag to enable incrementing the version of the application. If set to false the stored data will not change. Defaults to True.
            imports (list[any], optional): A List of import constraints to apply to all stack packs. Defaults to [].

        Raises:
            ValueError: If the stack pack name is not in the stack_packs

        Returns:
            Policy: The combined policy of all the stack packs
        """
        apps: List[UserApp] = []
        invalid_stacks = []
        for name, config in config.items():
            if name == UserPack.COMMON_APP_NAME:
                continue
            if name not in stack_packs:
                invalid_stacks.append(name)
                continue
            version = self.apps.get(name, None)
            app: UserApp = None
            if version is not None:
                try:
                    app = UserApp.get(UserApp.composite_key(self.id, name), version)
                    app.configuration = config
                    if increment_versions:
                        # Only increment version if there has been an attempted deploy on the current version, otherwise we can overwrite the state
                        latest_version = UserApp.get_latest_deployed_version(app.app_id)
                        if (
                            latest_version is not None
                            and latest_version.version >= app.version
                        ):
                            app.version = latest_version.version + 1
                            app.deployments = {}
                except DoesNotExist as e:
                    logger.info(
                        f"App {name} does not exist for pack id {self.id}. Creating a new one."
                    )
            if app is None:
                app = UserApp(
                    # This has to be a composite key so we can correlate the app with the pack
                    app_id=UserApp.composite_key(self.id, name),
                    version=1,
                    created_by=self.created_by,
                    created_at=datetime.datetime.now(),
                    configuration=config,
                    status=AppLifecycleStatus.NEW.value,
                )
            apps.append(app)

        if len(invalid_stacks) > 0:
            raise ValueError(f"Invalid stack names: {', '.join(invalid_stacks)}")

        # Run the packs in parallel and only store the iac if we are incrementing the version
        tasks = []
        for app in apps:
            subdir = Path(tmp_dir) / app.get_app_name()
            subdir.mkdir(exist_ok=True)
            sp = stack_packs[app.get_app_name()]
            tasks.append(
                app.run_app(
                    sp,
                    str(subdir.absolute()),
                    iac_storage,
                    binary_storage,
                    imports,
                )
            )
        policies = await asyncio.gather(*tasks)

        if increment_versions:
            for app in apps:
                app.save()
                self.apps[app.get_app_name()] = app.version

        # Combine the policies
        combined_policy = policies[0]
        for policy in policies[1:]:
            combined_policy.combine(policy)

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
            features=self.features,
            created_by=self.created_by,
            created_at=self.created_at,
        )


class UserStack(BaseModel):
    id: str
    owner: str
    region: Optional[str] = None
    assumed_role_arn: Optional[str] = None
    stack_packs: dict[str, AppModel] = Field(default_factory=dict)
    features: Optional[List[str]] = None
    created_by: str
    created_at: datetime.datetime
