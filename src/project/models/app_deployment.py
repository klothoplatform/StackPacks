import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pynamodb.attributes import (
    JSONAttribute,
    ListAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.models import Model
from typing_extensions import deprecated

from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.engine_service.engine_commands.run import (
    RunEngineRequest,
    RunEngineResult,
    run_engine,
)
from src.project import ConfigValues, StackPack
from src.project.common_stack import CommonStack
from src.util.aws.iam import Policy
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
    created_by: str = UnicodeAttribute()
    created_at: datetime = UTCDateTimeAttribute(default=datetime.utcnow)
    outputs: dict[str, str] = JSONAttribute(null=True)
    deployments: list[str] = ListAttribute(null=True)
    configuration: dict = JSONAttribute()
    display_name: str = UnicodeAttribute(null=True)
    policy: str = UnicodeAttribute(null=True)

    def app_id(self):
        return self.range_key.split("#")[0]

    def version(self):
        return int(self.range_key.split("#")[1]) if "#" in self.range_key else None

    def to_view_model(self):
        latest_deployed, status, reason = AppDeployment.get_status(
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
                latest_deployed.version() if latest_deployed else None
            ),
            status=status,
            status_reason=reason,
        )

    def __eq__(self, other):
        return (
            self.project_id == other.project_id
            and self.range_key == other.range_key
            and self.created_by == other.created_by
            and self.created_at == other.created_at
            and self.outputs == other.outputs
            and self.deployments == other.deployments
            and self.configuration == other.configuration
            and self.display_name == other.display_name
        )

    def global_tag(self):
        # Different services have different restrictions on the characters allowed in tags
        # Use this as the lowest common denominator
        # The engine should realistically do this sanitization, but for now it would just fail on deploy
        project = re.sub(r"[^\w :-]", "_", self.project_id)
        tag = f"{project}/{self.app_id()}"
        if len(tag) > 128:
            tag = f"{project[:128 - len(self.app_id()) - 1]}/{self.app_id()}"
        return tag

    def get_configurations(self) -> ConfigValues:
        return ConfigValues(self.configuration.items())

    def update_configurations(self, configuration: ConfigValues):
        self.update(actions=[AppDeployment.configuration.set(configuration)])

    def get_policy(self) -> Policy:
        return Policy(self.policy)

    async def update_policy(
        self,
        stack_pack: StackPack,
        app_dir: str,
        binary_storage: BinaryStorage,
        region: str,
        imports: list[any] = [],
        dry_run: bool = False,
    ):
        cfg = self.get_configurations()
        is_empty_config = True
        if len(self.configuration) > 0:
            for k, v in self.configuration.items():
                cfg = stack_pack.configuration[k]
                if cfg.default is None or v == cfg.default:
                    continue

                is_empty_config = False
                break

        logger.debug(f"{self.app_id()} has empty config: {is_empty_config}")
        policy = None
        if is_empty_config:
            policy_path = Path("policies") / f"{self.app_id()}.json"
            logger.debug(
                f"Checking if policy exists: {policy_path}: {policy_path.exists()}"
            )
            if policy_path.exists():
                policy = Policy(policy_path.read_text())

        if policy is None:
            constraints = stack_pack.to_constraints(cfg, region)
            constraints.extend(imports)
            if len(imports) == 0:
                common_modules = CommonStack([stack_pack], [])
                constraints.extend(common_modules.to_constraints({}, region))

            binary_storage.ensure_binary(Binary.ENGINE)
            engine_result: RunEngineResult = await run_engine(
                RunEngineRequest(
                    tag=self.global_tag(),
                    constraints=constraints,
                    tmp_dir=app_dir,
                )
            )
            if is_empty_config:
                policy_path = Path("policies") / f"{self.app_id()}.json"
                if not policy_path.exists():
                    # Shouldn't happen if policies are precomputed via scripts/cli.py policy_gen generate_policies
                    policy_path.parent.mkdir(parents=True, exist_ok=True)
                    policy_path.write_text(engine_result.policy)

            policy = Policy(engine_result.policy)
            for pol in stack_pack.additional_policies:
                additional_policies = Policy()
                additional_policies.policy = pol
                policy.combine(additional_policies)
        self.policy = str(policy)

        if not dry_run:
            self.save()

    async def run_app(
        self,
        stack_pack: StackPack,
        app_dir: str,
        binary_storage: BinaryStorage,
        region: str,
        imports: list[any] = [],
        dry_run: bool = False,
    ):
        constraints = stack_pack.to_constraints(self.get_configurations(), region)
        constraints.extend(imports)
        if len(imports) == 0:
            common_modules = CommonStack([stack_pack], [])
            constraints.extend(common_modules.to_constraints({}, region))

        binary_storage.ensure_binary(Binary.ENGINE)
        engine_result: RunEngineResult = await run_engine(
            RunEngineRequest(
                tag=self.global_tag(),
                constraints=constraints,
                tmp_dir=app_dir,
            )
        )

        self.policy = engine_result.policy
        if not dry_run:
            self.save()
        return engine_result

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
        return cls.get_status(project_id, app_id)[0]

    @classmethod
    def get_status(
        cls, project_id: str, app_id: str
    ) -> tuple["AppDeployment", "AppLifecycleStatus", str]:
        results = cls.query(
            project_id,
            AppDeployment.range_key.startswith(f"{app_id}#"),
            filter_condition=AppDeployment.deployments.exists(),  # Only include items where status is not null
            scan_index_forward=True,  # Sort in descending order
            page_size=10,  # Only check the ten most recent versions
        )
        local_state = None
        for app in results:
            for i in range(len(app.deployments), 0, -1):
                deployment = app.deployments[i - 1]
                hk, rk = WorkflowJob.composite_key_to_keys(deployment)
                try:
                    job = WorkflowJob.get(hk, rk)
                except WorkflowJob.DoesNotExist:
                    logger.error(f"Job {hk} # {rk} not found")
                    return app, AppLifecycleStatus.INSTALLED, None

                if local_state:
                    if job.job_type == WorkflowJobType.DESTROY.value:
                        if job.status == WorkflowJobStatus.SUCCEEDED.value:
                            return local_state
                    if local_state[1] == AppLifecycleStatus.INSTALLING:
                        return (
                            local_state[0],
                            AppLifecycleStatus.UPDATING,
                            job.status_reason,
                        )
                    elif local_state[1] == AppLifecycleStatus.INSTALL_FAILED:
                        return app, AppLifecycleStatus.UPDATE_FAILED, job.status_reason

                if job.job_type == WorkflowJobType.DEPLOY.value:
                    if job.status == WorkflowJobStatus.FAILED.value:
                        local_state = (
                            app,
                            AppLifecycleStatus.INSTALL_FAILED,
                            job.status_reason,
                        )
                    elif job.status == WorkflowJobStatus.SUCCEEDED.value:
                        return app, AppLifecycleStatus.INSTALLED, job.status_reason
                    elif job.status == WorkflowJobStatus.IN_PROGRESS.value:
                        local_state = (
                            app,
                            AppLifecycleStatus.INSTALLING,
                            job.status_reason,
                        )
                    elif (
                        job.status == WorkflowJobStatus.NEW.value
                        or job.status == WorkflowJobStatus.PENDING.value
                    ):
                        return app, AppLifecycleStatus.PENDING, job.status_reason
                    elif (
                        job.status == WorkflowJobStatus.CANCELED.value
                        or job.status == WorkflowJobStatus.SKIPPED.value
                    ):
                        continue
                    else:
                        return app, AppLifecycleStatus.UNKNOWN, job.status_reason
                elif job.job_type == WorkflowJobType.DESTROY.value:
                    if job.status == WorkflowJobStatus.FAILED.value:
                        return (
                            app,
                            AppLifecycleStatus.UNINSTALL_FAILED,
                            job.status_reason,
                        )
                    elif job.status == WorkflowJobStatus.SUCCEEDED.value:
                        return None, AppLifecycleStatus.UNINSTALLED, job.status_reason
                    elif job.status == WorkflowJobStatus.IN_PROGRESS.value:
                        return app, AppLifecycleStatus.UNINSTALLING, job.status_reason
                    elif (
                        job.status == WorkflowJobStatus.NEW.value
                        or job.status == WorkflowJobStatus.PENDING.value
                    ):
                        return app, AppLifecycleStatus.PENDING, job.status_reason
                    elif (
                        job.status == WorkflowJobStatus.CANCELED.value
                        or job.status == WorkflowJobStatus.SKIPPED.value
                    ):
                        continue
                    else:
                        return app, AppLifecycleStatus.UNKNOWN, job.status_reason
                else:
                    raise ValueError(f"Unknown job type {job.job_type}")
        if local_state:
            return local_state
        return None, AppLifecycleStatus.NEW, None

    @staticmethod
    def compose_range_key(app_id, version):
        return f"{app_id}#{version:08}"


class AppDeploymentView(BaseModel):
    app_id: str
    version: int
    created_by: str
    created_at: datetime
    configuration: ConfigValues = Field(default_factory=dict)
    display_name: Optional[str] = None
    outputs: Optional[dict[str, str]] = Field(default_factory=dict)
    last_deployed_version: Optional[int] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None


def get_resources(
    constraints: list,
) -> set[str]:
    return set(
        ":".join(c["node"].split(":")[:2])
        for c in constraints
        if c["scope"] == "application" and c["operator"] in ["add", "must_exist"]
    )
