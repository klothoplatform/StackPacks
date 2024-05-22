import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

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
from src.project import ConfigValues, StackPack, get_stack_packs
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import (
    AppDeployment,
    AppDeploymentView,
    get_resources,
)
from src.util.aws.iam import Policy
from src.util.logging import logger


class Project(Model):
    class Meta:
        table_name = os.environ.get("PROJECTS_TABLE_NAME", "Projects")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    id: str = UnicodeAttribute(hash_key=True)
    owner: str = UnicodeAttribute()
    region: str = UnicodeAttribute(null=True)
    assumed_role_arn: str = UnicodeAttribute(null=True)
    assumed_role_external_id: str = UnicodeAttribute(null=True)
    features: List[str] = ListAttribute(null=True)
    apps: dict[str, int] = JSONAttribute()
    created_by: str = UnicodeAttribute()
    created_at: datetime = UTCDateTimeAttribute(
        default=lambda: datetime.now(timezone.utc)
    )
    destroy_in_progress: bool = BooleanAttribute(default=False)

    def __eq__(self, other):
        return (
            self.id == other.id
            and self.owner == other.owner
            and self.region == other.region
            and self.assumed_role_arn == other.assumed_role_arn
            and self.assumed_role_external_id == other.assumed_role_external_id
            and self.features == other.features
            and self.apps == other.apps
            and self.created_by == other.created_by
            and self.created_at == other.created_at
            and self.destroy_in_progress == other.destroy_in_progress
        )

    def get_policy(self) -> Policy:
        p = Policy()
        for app in self.get_app_deployments():
            p.combine(Policy(app.policy))
        return p

    async def run_common_pack(
        self,
        stack_packs: List[StackPack],
        config: ConfigValues | None,
        features: list[str] | None,
        binary_storage: BinaryStorage,
        tmp_dir: Path,
        dry_run: bool = False,
    ):
        if features is None:
            features = self.features
        common_stack = CommonStack(stack_packs, features)
        common_version = self.apps.get(CommonStack.COMMON_APP_NAME, None)
        app: AppDeployment | None = None
        old_config: ConfigValues | None = None
        if common_version is not None:
            try:
                app = AppDeployment.get(
                    self.id,
                    AppDeployment.compose_range_key(
                        app_id=CommonStack.COMMON_APP_NAME, version=common_version
                    ),
                )
                old_config = app.get_configurations()
                if config is not None:
                    app.configuration = config
                else:
                    config = old_config

                # Only increment version if there has been an attempted deploy on the current version
                latest_version = AppDeployment.get_latest_deployed_version(
                    self.id, CommonStack.COMMON_APP_NAME
                )
                if (
                    latest_version is not None
                    and app is not None
                    and latest_version.version() >= app.version()
                ):
                    app.range_key = AppDeployment.compose_range_key(
                        app_id=app.app_id(), version=latest_version.version() + 1
                    )
                    app.deployments = {}
            except DoesNotExist as e:
                logger.info(
                    f"App {CommonStack.COMMON_APP_NAME} does not exist for pack id {self.id}. Creating a new one."
                )
        if app is None:
            if config is None:
                config = ConfigValues()
            try:
                latest = AppDeployment.get_latest_version(
                    project_id=self.id, app_id=CommonStack.COMMON_APP_NAME
                )
            except DoesNotExist:
                latest = None
            app = AppDeployment(
                # This has to be a composite key so we can correlate the app with the pack
                project_id=self.id,
                range_key=AppDeployment.compose_range_key(
                    app_id=CommonStack.COMMON_APP_NAME,
                    version=latest.version() + 1 if latest else 1,
                ),
                created_by=self.created_by,
                created_at=datetime.now(timezone.utc),
                configuration=config,
            )

        # Set the configuration for the common app (including hardcoded values for the pack id and health endpoint)
        health_endpoint_url = os.environ.get(
            "HEALTH_ENDPOINT_URL", "http://localhost:3000"
        )
        config["PackId"] = self.id
        config["HealthEndpointUrl"] = health_endpoint_url
        app.configuration = common_stack.final_config(config)

        resources_changed = True
        if old_config is not None:
            # Need to create a new stack based on the current applications (not `stack_packs`)
            # in case that changes requirements, which impacts the resources created.
            all_stack_packs = get_stack_packs()
            old_common_stack = CommonStack(
                [sp for sp in all_stack_packs.values() if sp.id in self.apps.keys()],
                self.features,
            )
            old_resources = get_resources(
                old_common_stack.to_constraints(old_config or {}, self.region)
            )
            new_resources = get_resources(
                common_stack.to_constraints(config, self.region)
            )
            diff = new_resources ^ old_resources
            logger.debug(
                f"common:: old: {old_resources}; new: {new_resources}; diff: {diff}"
            )
            resources_changed = len(diff) > 0

        if resources_changed:
            # Run the packs in parallel and only store the iac if we are incrementing the version
            subdir = tmp_dir / app.app_id()
            subdir.mkdir(exist_ok=True)
            await app.update_policy(
                common_stack,
                str(subdir.absolute()),
                binary_storage,
                self.region,
            )

        if not dry_run:
            app.save()
            self.features = features
            self.apps[CommonStack.COMMON_APP_NAME] = app.version()
            self.save()

    async def run_packs(
        self,
        stack_packs: dict[str, StackPack],
        config: dict[str, ConfigValues],
        tmp_dir: Path,
        binary_storage: BinaryStorage = None,
        increment_versions: bool = True,
        imports: list = [],
    ):
        """Run the stack packs with the given configuration and return the combined policy

        Args:
            stack_packs (dict[str, StackPack]): a dictionary of stack packs where the key is the name of the stack pack
            config (dict[str, ConfigValues]): a dictionary of configurations where the key is the name of the stack pack
            tmp_dir (str): the temporary directory to store the files related to the engine execution of the stack pack
            increment_versions (bool, optional): A flag to enable incrementing the version of the application. If set to false the stored data will not change. Defaults to True.
            imports (list[any], optional): A List of import constraints to apply to all stack packs. Defaults to [].

        Raises:
            ValueError: If the stack pack name is not in the stack_packs
        """
        apps: List[AppDeployment] = []
        invalid_stacks = []
        for app_id, app_config in config.items():
            if app_id == CommonStack.COMMON_APP_NAME:
                continue
            if app_id not in stack_packs:
                invalid_stacks.append(app_id)
                continue
            version = self.apps.get(app_id, None)
            app: AppDeployment | None = None
            if version is not None:
                try:
                    app = AppDeployment.get(
                        self.id,
                        AppDeployment.compose_range_key(app_id=app_id, version=version),
                    )
                    app.configuration = app_config
                    if increment_versions:
                        # Only increment version if there has been an attempted deploy on the current version, otherwise we can overwrite the state
                        latest_version = AppDeployment.get_latest_deployed_version(
                            self.id, app_id
                        )
                        if (
                            latest_version is not None
                            and latest_version.version() >= app.version()
                        ):
                            app.range_key = AppDeployment.compose_range_key(
                                app_id=app.app_id(),
                                version=latest_version.version() + 1,
                            )
                            app.deployments = {}
                    logger.debug(f"updated app {app}")
                except DoesNotExist as e:
                    logger.info(
                        f"App {app_id} does not exist for pack id {self.id}. Creating a new one."
                    )
            if app is None:
                try:
                    latest = AppDeployment.get_latest_version(
                        project_id=self.id, app_id=app_id
                    )
                except DoesNotExist:
                    latest = None
                app = AppDeployment(
                    # This has to be a composite key so we can correlate the app with the pack
                    project_id=self.id,
                    range_key=AppDeployment.compose_range_key(
                        app_id=app_id, version=latest.version() + 1 if latest else 1
                    ),
                    created_by=self.created_by,
                    created_at=datetime.now(timezone.utc),
                    configuration=app_config,
                    display_name=stack_packs[app_id].name,
                )
                logger.debug(f"added app {app}")
            apps.append(app)

        if len(invalid_stacks) > 0:
            raise ValueError(f"Invalid stack names: {', '.join(invalid_stacks)}")

        old_resources = set()
        for app_id, version in self.apps.items():
            if app_id in stack_packs:
                app = AppDeployment.get(
                    self.id,
                    AppDeployment.compose_range_key(app_id=app_id, version=version),
                )
                old_resources.update(
                    get_resources(
                        stack_packs[app_id].to_constraints(
                            app.get_configurations(), self.region
                        )
                    )
                )

        new_resources = set()
        for app in apps:
            new_resources.update(
                get_resources(
                    stack_packs[app.app_id()].to_constraints(
                        app.get_configurations(), self.region
                    )
                )
            )
        diff = new_resources ^ old_resources
        logger.debug(f"pack:: old: {old_resources}; new: {new_resources}; diff: {diff}")

        if len(diff) > 0:
            # Run the packs in parallel
            tasks = []
            for app in apps:
                app_id = app.app_id()
                subdir = tmp_dir / app.app_id()
                subdir.mkdir(exist_ok=True)
                sp = stack_packs[app.app_id()]
                tasks.append(
                    app.update_policy(
                        sp,
                        str(subdir.absolute()),
                        binary_storage,
                        self.region,
                        imports,
                        dry_run=not increment_versions,
                    )
                )
            await asyncio.gather(*tasks)

        for app in apps:
            if increment_versions:
                app.save()
            self.apps[app.app_id()] = app.version()

        if increment_versions:
            self.save()

    def to_view_model(self):
        apps = {}
        policy = Policy()
        for app in self.get_app_deployments():
            apps[app.app_id()] = app.to_view_model()
            policy.combine(Policy(app.policy))

        return ProjectView(
            id=self.id,
            owner=self.owner,
            region=self.region,
            assumed_role_arn=self.assumed_role_arn,
            assumed_role_external_id=self.assumed_role_external_id,
            stack_packs=apps,
            features=self.features,
            created_by=self.created_by,
            created_at=self.created_at,
            policy=str(policy),
        )

    def common_stackpack(self) -> CommonStack:
        """Get the common stackpack for the project based on the project's apps and features"""
        return CommonStack(self.stack_packs(), self.features)

    def stack_packs(self) -> List[StackPack]:
        """Get the stack packs for the project app deployments associated with the project"""
        sps = get_stack_packs()
        return [sps[app_id] for app_id in self.apps.keys() if app_id in sps]

    def get_app_deployments(self) -> Iterator[AppDeployment]:
        """Get the app deployments associated with the project using a batch get operation"""
        keys = [
            (
                self.id,
                AppDeployment.compose_range_key(app_id=app_id, version=version),
            )
            for app_id, version in self.apps.items()
        ]
        return AppDeployment.batch_get(keys)


class ProjectView(BaseModel):
    id: str
    owner: str
    region: Optional[str] = None
    assumed_role_arn: Optional[str] = None
    assumed_role_external_id: Optional[str] = None
    stack_packs: dict[str, AppDeploymentView] = Field(default_factory=dict)
    features: Optional[List[str]] = None
    created_by: str
    created_at: datetime
    policy: Optional[str] = None
