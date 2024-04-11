import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

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

from src.deployer.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowType,
)
from src.engine_service.binaries.fetcher import BinaryStorage
from src.project import ConfigValues, StackPack
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import (
    AppDeployment,
    AppDeploymentView,
    AppLifecycleStatus,
    get_resources,
)
from src.util.aws.iam import Policy
from src.util.logging import logger


class Project(Model):
    COMMON_APP_NAME = "common"

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

    def get_workflow_runs(
        self,
        *,
        workflow_type: Optional[WorkflowType],
        status: Optional[WorkflowRunStatus],
        app_id: Optional[str],
    ) -> Iterable[WorkflowRun]:
        range_key_condition = WorkflowRun.range_key.startswith(
            f"{workflow_type.value}#{app_id if app_id is not None else ''}"
        )
        filter_condition = (
            WorkflowRun.status == status.value if status is not None else None
        )
        results = WorkflowRun.query(
            hash_key=self.id,
            range_key_condition=(
                range_key_condition if workflow_type is not None else None
            ),
            filter_condition=filter_condition,
        )
        if workflow_type is None and app_id:
            return filter(lambda x: x.app_id() == app_id, results)

    def get_policy(self) -> Policy:
        p = Policy()
        for app_id, version in self.apps.items():
            app = AppDeployment.get(
                self.id,
                AppDeployment.compose_range_key(app_id=app_id, version=version),
            )
            p.combine(Policy(app.policy))
        return p

    async def run_base(
        self,
        stack_packs: List[StackPack],
        config: ConfigValues,
        binary_storage: BinaryStorage,
        tmp_dir: Path,
        dry_run: bool = False,
    ):
        base_stack = CommonStack(stack_packs, self.features)
        base_version = self.apps.get(Project.COMMON_APP_NAME, None)
        app: AppDeployment | None = None
        old_config: ConfigValues | None = None
        if base_version is not None:
            try:
                app = AppDeployment.get(
                    self.id,
                    AppDeployment.compose_range_key(
                        app_id=Project.COMMON_APP_NAME, version=base_version
                    ),
                )
                old_config = app.get_configurations()
                app.configuration = config

                # Only increment version if there has been an attempted deploy on the current version
                latest_version = AppDeployment.get_latest_deployed_version(
                    project_id=self.id, app_id=Project.COMMON_APP_NAME
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
                    f"App {Project.COMMON_APP_NAME} does not exist for pack id {self.id}. Creating a new one."
                )
        if app is None:
            app = AppDeployment(
                # This has to be a composite key so we can correlate the app with the pack
                project_id=self.id,
                range_key=AppDeployment.compose_range_key(
                    app_id=Project.COMMON_APP_NAME, version=1
                ),
                created_by=self.created_by,
                created_at=datetime.now(timezone.utc),
                configuration=config,
                status=AppLifecycleStatus.NEW.value,
            )
        health_endpoint_url = os.environ.get(
            "HEALTH_ENDPOINT_URL", "http://localhost:3000"
        )
        app.configuration.update(
            {"PackId": self.id, "HealthEndpointUrl": health_endpoint_url}
        )

        resources_changed = False
        if old_config is not None:
            old_resources = get_resources(base_stack.to_constraints(old_config))
            new_resources = get_resources(base_stack.to_constraints(config))
            diff = new_resources ^ old_resources
            logger.debug(
                f"common:: old: {old_resources}; new: {new_resources}; diff: {diff}"
            )
            resources_changed = len(diff) > 0

        if resources_changed:
            # Run the packs in parallel and only store the iac if we are incrementing the version
            subdir = tmp_dir / app.app_id()
            subdir.mkdir(exist_ok=True)
            await app.run_app(base_stack, str(subdir.absolute()), binary_storage)

        if not dry_run:
            app.save()
            self.apps[Project.COMMON_APP_NAME] = app.version()

    async def run_pack(
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
            if app_id == Project.COMMON_APP_NAME:
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
                            project_id=self.id, app_id=app_id
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
                app = AppDeployment(
                    # This has to be a composite key so we can correlate the app with the pack
                    project_id=self.id,
                    range_key=AppDeployment.compose_range_key(app_id=app_id, version=1),
                    created_by=self.created_by,
                    created_at=datetime.now(timezone.utc),
                    configuration=app_config,
                    status=AppLifecycleStatus.NEW.value,
                    display_name=(
                        stack_packs[app_id].name
                        if stack_packs.get(app_id, None)
                        else app_id
                    ),
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
                        stack_packs[app_id].to_constraints(app.get_configurations())
                    )
                )

        new_resources = set()
        for app in apps:
            new_resources.update(
                get_resources(
                    stack_packs[app.app_id()].to_constraints(app.get_configurations())
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
                    app.run_app(
                        sp,
                        str(subdir.absolute()),
                        binary_storage,
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
        for k, v in self.apps.items():
            try:
                app = AppDeployment.get(
                    self.id, AppDeployment.compose_range_key(app_id=k, version=v)
                )
                apps[k] = app.to_view_model()
            except DoesNotExist as e:
                logger.error(f"App {k}v{v} does not exist for pack id {self.id}.")
                raise e
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
            policy=str(self.get_policy()),
        )


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
