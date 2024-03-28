from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel

from src.deployer.models.workflow_job import (
    WorkflowJobStatus,
    WorkflowJob,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import (
    WorkflowRunStatus,
    WorkflowRun,
    WorkflowType,
)


class WorkflowRunSummary(BaseModel):
    id: str
    run_number: int
    workflow_type: WorkflowType
    created_at: datetime
    initiated_by: str
    initiated_at: Optional[datetime]
    completed_at: Optional[datetime]
    status: WorkflowRunStatus
    app_id: Optional[str]

    @classmethod
    def from_workflow_run(cls, run: WorkflowRun):
        return cls(
            id=run.composite_key(),
            created_at=run.created_at,
            initiated_by=run.initiated_by,
            initiated_at=run.initiated_at,
            completed_at=run.completed_at,
            status=WorkflowRunStatus[run.status],
            app_id=run.app_id(),
            run_number=run.run_number(),
            workflow_type=WorkflowType[run.type],
        )


class WorkflowJobView(BaseModel):
    id: str
    job_number: int
    status: WorkflowJobStatus
    title: str
    job_type: WorkflowJobType
    initiated_at: Optional[datetime]
    completed_at: Optional[datetime]
    status_reason: str
    dependencies: List[str]
    outputs: dict[str, str]

    @classmethod
    def from_workflow_job(cls, job: WorkflowJob):
        return cls(
            id=job.composite_key(),
            job_number=job.job_number,
            job_type=job.job_type,
            status=job.status,
            title=job.title,
            initiated_at=job.initiated_at,
            completed_at=job.completed_at,
            status_reason=job.status_reason,
            dependencies=job.dependencies,
            outputs=job.outputs or {},
        )


class WorkflowRunView(BaseModel):
    id: str
    run_number: int
    project_id: str
    created_at: datetime
    workflow_type: WorkflowType
    initiated_by: str
    initiated_at: Optional[datetime]
    completed_at: Optional[datetime]
    status: WorkflowRunStatus
    app_id: Optional[str]
    jobs: List[WorkflowJobView]

    @classmethod
    def from_workflow_run(cls, run: WorkflowRun):
        jobs: List[WorkflowJob] = list(run.get_jobs())

        return cls(
            id=run.composite_key(),
            run_number=run.run_number(),
            project_id=run.project_id,
            workflow_type=WorkflowType[run.type],
            created_at=run.created_at,
            initiated_by=run.initiated_by,
            initiated_at=run.initiated_at,
            completed_at=run.completed_at,
            status=WorkflowRunStatus[run.status],
            app_id=run.app_id(),
            jobs=[WorkflowJobView.from_workflow_job(job) for job in jobs],
        )
