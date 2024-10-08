from datetime import datetime, timezone

from src.deployer.models.workflow_job import WorkflowJob, WorkflowJobStatus
from src.deployer.models.workflow_run import WorkflowRun, WorkflowRunStatus
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from src.util import analytics
from src.util.logging import logger


# cancel_in_progress_jobs can be used to cancel all jobs in progress or only those that have not yet started
# this just marks them as canceled in the table -- it does not stop ongoing operations
def abort_workflow_run(
    run: WorkflowRun,
    cancel_in_progress_jobs: bool = False,
    default_run_status: WorkflowRunStatus = None,
):
    project = Project.get(run.project_id)
    project.update(
        actions=[
            Project.destroy_in_progress.set(False),
        ],
    )
    if default_run_status is None:
        default_run_status = WorkflowRunStatus.CANCELED
    logger.info(f"Aborting workflow run {run.composite_key()}")
    if run.status not in [
        WorkflowRunStatus.NEW.value,
        WorkflowRunStatus.IN_PROGRESS.value,
        WorkflowRunStatus.PENDING.value,
    ]:
        logger.info(
            f"Workflow run {run.composite_key()} is already in a terminal state"
        )
        return
    jobs = run.get_jobs()
    failed = False
    has_in_progress_jobs = False
    failed_job_number = None
    for job in jobs:
        if job.status in [WorkflowJobStatus.PENDING.value, WorkflowRunStatus.NEW.value]:
            job.update(
                actions=[
                    WorkflowJob.status.set(WorkflowJobStatus.CANCELED.value),
                    WorkflowJob.status_reason.set(
                        "Workflow job canceled due to early termination of workflow run"
                    ),
                    WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
                ]
            )
        elif job.status in [
            WorkflowJobStatus.SUCCEEDED.value,
            WorkflowJobStatus.SKIPPED.value,
        ]:
            continue
        elif job.status == WorkflowJobStatus.IN_PROGRESS.value:
            if cancel_in_progress_jobs:
                job.update(
                    actions=[
                        WorkflowJob.status.set(WorkflowJobStatus.CANCELED.value),
                        WorkflowJob.status_reason.set(
                            "Workflow job canceled due to early termination of workflow run"
                        ),
                        WorkflowJob.completed_at.set(datetime.now(timezone.utc)),
                    ]
                )
            else:
                has_in_progress_jobs = True
        elif job.status == WorkflowJobStatus.FAILED.value:
            failed = True
            failed_job_number = job.job_number

    if not has_in_progress_jobs:
        run.update(
            actions=[
                WorkflowRun.status.set(
                    WorkflowRunStatus.FAILED.value
                    if failed
                    else default_run_status.value
                ),
                WorkflowRun.status_reason.set(
                    f"Workflow run failed at job {failed_job_number}"
                    if failed
                    else "Workflow run aborted"
                ),
                WorkflowRun.completed_at.set(datetime.now(timezone.utc)),
            ]
        )


def complete_workflow_run(run: WorkflowRun) -> WorkflowRunStatus | None:
    try:
        logger.info(f"Completing workflow run {run.composite_key()}")
        jobs = run.get_jobs()
        failed = False
        canceled = False
        for job in jobs:
            if job.status == WorkflowJobStatus.FAILED.value:
                failed = True
            elif job.status == WorkflowJobStatus.CANCELED.value:
                canceled = True
            elif job.status not in [
                WorkflowJobStatus.SUCCEEDED.value,
                WorkflowJobStatus.SKIPPED.value,
            ]:
                raise ValueError(
                    f"Workflow job {job.composite_key()} has not completed"
                )

        if canceled and not failed:
            run.update(
                actions=[
                    WorkflowRun.status.set(WorkflowRunStatus.CANCELED.value),
                    WorkflowRun.status_reason.set("Workflow run canceled"),
                    WorkflowRun.completed_at.set(datetime.now(timezone.utc)),
                ]
            )

        elif failed:
            run.update(
                actions=[
                    WorkflowRun.status.set(WorkflowRunStatus.FAILED.value),
                    WorkflowRun.status_reason.set("Workflow run failed"),
                    WorkflowRun.completed_at.set(datetime.now(timezone.utc)),
                ]
            )
        else:
            run.update(
                actions=[
                    WorkflowRun.status.set(WorkflowRunStatus.SUCCEEDED.value),
                    WorkflowRun.status_reason.set("Workflow run succeeded"),
                    WorkflowRun.completed_at.set(datetime.now(timezone.utc)),
                ]
            )

        end_status = (
            WorkflowRunStatus.CANCELED
            if canceled
            else WorkflowRunStatus.FAILED if failed else WorkflowRunStatus.SUCCEEDED
        )
        return end_status

    except Exception as e:
        logger.error(f"Error completing workflow run {run.composite_key()}: {e}")
        return None
    finally:
        project = Project.get(run.project_id)
        project.update(
            actions=[
                Project.destroy_in_progress.set(False),
            ],
        )
        analytics.track(
            event="WorkflowRunCompleted",
            user_id=run.initiated_by,
            properties={
                "project_id": run.project_id,
                "run_id": run.composite_key(),
                "status": run.status,
                "type": run.type,
            },
        )


def start_workflow_run(run: WorkflowRun):
    try:
        logger.info(f"Starting workflow run {run.composite_key()}")
        jobs = run.get_jobs()
        run.update(
            actions=[
                WorkflowRun.status.set(WorkflowRunStatus.IN_PROGRESS.value),
                WorkflowRun.status_reason.set("Workflow run in progress"),
                WorkflowRun.initiated_at.set(datetime.now(timezone.utc)),
            ]
        )
        project = Project.get(run.project_id)
        for job in jobs:
            job.update(
                actions=[
                    WorkflowJob.status.set(WorkflowJobStatus.PENDING.value),
                    WorkflowJob.status_reason.set("Workflow job pending"),
                ]
            )
            app = AppDeployment.get(
                project.id,
                AppDeployment.compose_range_key(
                    app_id=job.modified_app_id(),
                    version=job.modified_app_version(),
                ),
            )
            app.update(
                actions=[
                    AppDeployment.deployments.set(
                        (
                            AppDeployment.deployments.append([job.composite_key()])
                            if app.deployments
                            else [job.composite_key()]
                        ),
                    ),
                ]
            )
        analytics.track(
            event="WorkflowRunStarted",
            user_id=run.initiated_by,
            properties={
                "project_id": run.project_id,
                "run_id": run.composite_key(),
                "status": run.status,
                "type": run.type,
            },
        )
    except Exception as e:
        logger.error(f"Error starting workflow run {run.composite_key()}: {e}")
        abort_workflow_run(run, cancel_in_progress_jobs=True)
        raise e
