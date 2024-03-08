import asyncio
import datetime
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pynamodb.attributes import JSONAttribute, UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.exceptions import DoesNotExist
from pynamodb.models import Model

from src.stack_pack import ConfigValues, StackPack
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.models.user_app import AppModel, UserApp
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
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
        iac_storage: IacStorage,
        tmp_dir: str,
        dry_run: bool = False,
    ) -> Policy:
        base_stack = CommonStack(stack_packs)
        base_version = self.apps.get(UserPack.COMMON_APP_NAME, None)
        app: UserApp = None
        if base_version is not None:
            try:
                app = UserApp.get(
                    UserApp.composite_key(self.id, UserPack.COMMON_APP_NAME),
                    base_version,
                )
                # Only increment version if there has been an attempted deploy on the current version
                latest_version = UserApp.get_latest_version_with_status(app.app_id)
                if latest_version is not None and latest_version.version == app.version:
                    app.version = app.version + 1
            except DoesNotExist as e:
                logger.info(
                    f"App {UserPack.COMMON_APP_NAME} does not exist for pack id {self.id}. Creating a new one."
                )
        if app is None:
            app = UserApp(
                app_id=UserPack.COMMON_APP_NAME,
                version=1,
                created_by=self.created_by,
                created_at=datetime.datetime.now(),
                configuration=config,
            )
        # Run the packs in parallel and only store the iac if we are incrementing the version
        subdir = Path(tmp_dir) / app.get_app_name()
        subdir.mkdir(exist_ok=True)
        policy = await app.run_app(base_stack, str(subdir.absolute()), iac_storage)

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
        base_stack = CommonStack([sp for k, sp in stack_packs.items()])
        invalid_stacks = []
        for name, config in config.items():
            if name is UserPack.COMMON_APP_NAME:
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
                        latest_version = UserApp.get_latest_version_with_status(
                            app.app_id
                        )
                        if (
                            latest_version is not None
                            and latest_version.version == app.version
                        ):
                            app.version = app.version + 1
                except DoesNotExist as e:
                    logger.info(
                        f"App {name} does not exist for pack id {self.id}. Creating a new one."
                    )
            if app is None:
                app = UserApp(
                    app_id=name,
                    version=1,
                    created_by=self.created_by,
                    created_at=datetime.datetime.now(),
                    configuration=config,
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
            # Extend the base resources to the stack pack in case they are used in the stack pack
            for id, properties in base_stack.base.resources.items():
                import_constraints = [
                    c["node"] for c in imports if c["operator"] == "import"
                ]
                if id not in import_constraints:
                    sp.base.resources.update({id: properties})
            tasks.append(
                app.run_app(
                    sp,
                    str(subdir.absolute()),
                    iac_storage,
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
