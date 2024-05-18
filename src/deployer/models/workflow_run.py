import os
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, NamedTuple, Optional

from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.exceptions import PutError
from pynamodb.models import Model

from src.deployer.models.workflow_job import WorkflowJob
from src.util.logging import logger


class WorkflowRunStatus(Enum):
    CANCELED = "CANCELED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NEW = "NEW"
    PENDING = "PENDING"


class WorkflowType(Enum):
    DEPLOY = "DEPLOY"
    DESTROY = "DESTROY"

    @staticmethod
    def from_str(label: str):
        label = label.upper()
        try:
            return WorkflowType[label]
        except KeyError:
            return ValueError(f"Invalid WorkflowType: {label}")


class WorkflowRunRangeKey(NamedTuple):
    run_id: str
    app_id: Optional[str]


class WorkflowRun(Model):
    class Meta:
        table_name = os.environ.get("WORKFLOW_RUNS_TABLE_NAME", "WorkflowRuns")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    project_id: str = UnicodeAttribute(hash_key=True)
    # composite key: workflow_type#app_id#run_number
    range_key: str = UnicodeAttribute(range_key=True)
    type: str = UnicodeAttribute()
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute(null=True)
    created_at: datetime = UTCDateTimeAttribute(
        default=lambda: datetime.now(timezone.utc)
    )
    initiated_at: datetime = UTCDateTimeAttribute(null=True)
    completed_at: datetime = UTCDateTimeAttribute(null=True)
    initiated_by: str = UnicodeAttribute()
    notification_email: str = UnicodeAttribute(null=True)

    def workflow_type(self) -> str:
        return self.range_key.split("#")[0]

    def app_id(self) -> str:
        return self.range_key.split("#")[1]

    def run_number(self) -> int:
        return int(self.range_key.split("#")[2])

    # todo: update get_latest_run to use new keys
    def get_jobs(self) -> Iterable[WorkflowJob]:
        return WorkflowJob.query(
            self.composite_key(),
        )

    @classmethod
    def get_latest_run(
        cls,
        project_id: str,
        workflow_type: Optional[WorkflowType] = None,
        app_id: Optional[str] = None,
    ):

        if workflow_type is None:
            # TODO: consider an LSI for this query
            # get the latest run for the project by created_at
            latest_run = None
            for run in cls.query(project_id):
                if latest_run is None or run.created_at > latest_run.created_at:
                    latest_run = run
            return latest_run

        for run in cls.query(
            project_id,
            range_key_condition=cls.range_key.startswith(
                f"{workflow_type.value}#{app_id if app_id else ''}#"
            ),
            scan_index_forward=False,
            limit=1,
        ):
            return run

    def composite_key(self):
        return f"{self.project_id}#{self.range_key}"

    def job_id(self):
        return WorkflowJob.compose_partition_key(
            project_id=self.project_id,
            workflow_type=self.workflow_type(),
            owning_app_id=self.app_id(),
            run_number=self.run_number(),
        )

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, WorkflowRun):
            return False
        return (
            self.project_id == __value.project_id
            and self.range_key == __value.range_key
            and self.type == __value.type
            and self.status == __value.status
            and self.status_reason == __value.status_reason
            and self.initiated_at == __value.initiated_at
            and self.initiated_by == __value.initiated_by
            and self.completed_at == __value.completed_at
            and self.created_at == __value.created_at
            and self.app_id == __value.app_id
            and self.notification_email == __value.notification_email
        )

    @staticmethod
    def compose_range_key(workflow_type: str, app_id: str | None, run_number: int):
        return f"{workflow_type}#{app_id if app_id else ''}#{run_number:08}"

    @staticmethod
    def get_workflow_runs(
        porject_id: str,
        *,
        workflow_type: Optional[WorkflowType],
        status: Optional[WorkflowRunStatus],
        app_id: Optional[str],
    ) -> Iterable["WorkflowRun"]:
        range_key_condition = WorkflowRun.range_key.startswith(
            f"{workflow_type.value}#{app_id if app_id is not None else ''}"
        )
        filter_condition = (
            WorkflowRun.status == status.value if status is not None else None
        )
        results = WorkflowRun.query(
            hash_key=porject_id,
            range_key_condition=(
                range_key_condition if workflow_type is not None else None
            ),
            filter_condition=filter_condition,
        )
        if workflow_type is None and app_id:
            return filter(lambda x: x.app_id() == app_id, results)

    @classmethod
    def create(
        cls,
        project_id: str,
        workflow_type: WorkflowType,
        app_id: Optional[str] = None,
        initiated_by: str = None,
        notification_email: str = None,
    ):
        run = cls(
            project_id=project_id,
            type=workflow_type.value,
            status=WorkflowRunStatus.NEW.value,
            initiated_by=initiated_by,
            notification_email=notification_email,
        )
        for i in range(5):
            previous_run = cls.get_latest_run(project_id, workflow_type, app_id)
            run_number = previous_run.run_number() + 1 if previous_run else 1
            run.range_key = cls.compose_range_key(
                workflow_type=workflow_type.value, app_id=app_id, run_number=run_number
            )
            try:
                run.save(
                    condition=(
                        WorkflowRun.project_id.does_not_exist()
                        & WorkflowRun.range_key.does_not_exist()
                    )
                )
                break
            except PutError as e:
                logger.warn(f"Failed to save run: {e}; attempt={i + 1}")
                if i == 4:
                    raise e

        return run
