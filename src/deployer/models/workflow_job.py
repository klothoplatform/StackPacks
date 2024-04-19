import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pynamodb.attributes import (
    JSONAttribute,
    ListAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.exceptions import PutError
from pynamodb.models import Model

from src.project import get_app_name
from src.util.logging import logger


class WorkflowJobStatus(Enum):
    SKIPPED = "SKIPPED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NEW = "NEW"
    PENDING = "PENDING"
    CANCELED = "CANCELED"


class WorkflowJobType(Enum):
    DEPLOY = "DEPLOY"
    DESTROY = "DESTROY"


class WorkflowJob(Model):

    class Meta:
        table_name = os.environ.get("WORKFLOW_JOBS_TABLE_NAME", "WorkflowJobs")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    # composite key: project_id#workflow_type#app_id#run_number
    partition_key: str = UnicodeAttribute(hash_key=True)
    job_number: int = NumberAttribute(range_key=True)
    iac_stack_composite_key: str = UnicodeAttribute(null=True)
    job_type: str = UnicodeAttribute()
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute()
    created_at: datetime = UTCDateTimeAttribute(
        default=lambda: datetime.now(timezone.utc)
    )
    initiated_at: datetime = UTCDateTimeAttribute(null=True)
    title: str = UnicodeAttribute()
    initiated_by: str = UnicodeAttribute()
    completed_at: datetime = UTCDateTimeAttribute(null=True)
    # List of composite keys of jobs that this job depends on (project_id#workflow_type#app_id#run_number#job_number)
    dependencies: list[str] = ListAttribute(of=UnicodeAttribute, default=list)
    modified_app_id: str = UnicodeAttribute()
    outputs: dict[str, str] = JSONAttribute(null=True)

    def project_id(self) -> str:
        return self.partition_key.split("#")[0]

    def workflow_type(self) -> str:
        return self.partition_key.split("#")[1]

    # this is the app_id of the app owns the workflow run associated with this job
    def owning_app_id(self) -> str:
        return self.partition_key.split("#")[2]

    def run_number(self) -> int:
        return int(self.partition_key.split("#")[3])

    @staticmethod
    def get_latest_job(partition_key: str):
        for job in WorkflowJob.query(partition_key, scan_index_forward=False, limit=1):
            return job

    @staticmethod
    def compose_partition_key(
        project_id: str, workflow_type: str, owning_app_id: str | None, run_number: int
    ) -> str:
        return f"{project_id}#{workflow_type}#{owning_app_id if owning_app_id else ''}#{run_number:08}"

    def composite_key(self) -> str:
        return f"{self.partition_key}#{self.job_number}"

    @staticmethod
    def composite_key_to_keys(composite_key: str) -> tuple[str, int]:
        partition_key, job_number = composite_key.rsplit("#", 1)
        return partition_key, int(job_number)

    def run_composite_key(self) -> str:
        return self.partition_key

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, WorkflowJob):
            return False
        return (
            self.partition_key == __value.partition_key
            and self.job_number == __value.job_number
            and self.iac_stack_composite_key == __value.iac_stack_composite_key
            and self.job_type == __value.job_type
            and self.status == __value.status
            and self.status_reason == __value.status_reason
            and self.initiated_by == __value.initiated_by
            and self.initiated_at == __value.initiated_at
            and self.created_at == __value.created_at
            and self.completed_at == __value.completed_at
            and self.modified_app_id == __value.modified_app_id
            and self.dependencies == __value.dependencies
            and self.outputs == __value.outputs
            and self.title == __value.title
        )

    @classmethod
    def get_latest_job(cls, partition_key: str):
        for job in cls.query(partition_key, scan_index_forward=False, limit=1):
            return job

    @classmethod
    def get_jobs(cls, run_composite_key):
        return cls.query(run_composite_key)

    @classmethod
    def create_job(
        cls,
        partition_key: str,
        job_type: WorkflowJobType,
        modified_app_id: str,
        initiated_by: str,
        dependencies: Optional[list[str]] = None,
        title: Optional[str] = None,
    ):
        if dependencies is None:
            dependencies = []

        if title is None:
            title = resolve_title(job_type, modified_app_id)
        job = cls(
            partition_key=partition_key,
            job_type=job_type.value,
            modified_app_id=modified_app_id,
            status=WorkflowJobStatus.NEW.value,
            status_reason="",
            initiated_by=initiated_by,
            dependencies=dependencies,
            title=title,
        )

        for i in range(5):
            try:
                last_job = cls.get_latest_job(partition_key)
                job_number = last_job.job_number + 1 if last_job else 1
                job.job_number = job_number
                job.save(
                    condition=WorkflowJob.partition_key.does_not_exist()
                    & WorkflowJob.job_number.does_not_exist()
                )
                break
            except PutError:
                logger.warning(f"Failed to save job {job.job_number}; attempt={i + 1}")
                if i == 4:
                    raise

        return job


def resolve_title(job_type: WorkflowJobType, modified_app_id: str | None) -> str:
    if modified_app_id:
        app_name = get_app_name(modified_app_id)
    else:
        app_name = "all apps"

    if job_type == WorkflowJobType.DEPLOY:
        return f"Deploy {app_name}"
    elif job_type == WorkflowJobType.DESTROY:
        return f"Destroy {app_name}"
    else:
        return f"{job_type}{' ' + app_name if app_name else ''}"
