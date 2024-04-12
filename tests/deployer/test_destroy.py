from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiounittest

from src.deployer.destroy import (
    DeploymentResult,
    StackDeploymentRequest,
    destroy_app,
    destroy_applications,
    execute_destroy_all_workflow,
    execute_destroy_single_workflow,
    run_concurrent_destroys,
    run_destroy,
    run_destroy_application,
)
from src.deployer.models.pulumi_stack import PulumiStack
from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import WorkflowRun, WorkflowType
from src.deployer.pulumi.manager import AppManager
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from src.project.storage.iac_storage import IaCDoesNotExistError, IacStorage
from tests.test_utils.pynamo_test import PynamoTest


class TestDestroy(PynamoTest, aiounittest.AsyncTestCase):
    models = [AppDeployment, Project, PulumiStack, WorkflowJob, WorkflowRun]

    def setUp(self):
        super().setUp()
        self.project = Project(
            id="project",
            region="region",
            assumed_role_arn="arn",
            assumed_role_external_id="external_id",
            apps={"app1": 1, Project.COMMON_APP_NAME: 1},
            created_by="user",
            owner="user",
        )
        self.project.save()

        self.app1 = AppDeployment(
            project_id="project",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=AppLifecycleStatus.INSTALLED.value,
            status_reason="reason",
            configuration={"key1": "value1"},
            outputs={"URL": "url"},
            deployments=["deployment1"],
        )
        self.app1.save()

        self.common_app = AppDeployment(
            project_id="project",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="user",
            status=AppLifecycleStatus.INSTALLED.value,
            status_reason="reason",
            configuration={"key1": "value1"},
            deployments=["deployment1"],
        )
        self.common_app.save()
        self.pulumi_config = {}
        self.tmp_dir = Path("/tmp")

    @patch("src.deployer.destroy.AppDeployer")
    @patch("src.deployer.destroy.AppBuilder")
    @patch("src.deployer.destroy.DeploymentDir")
    async def test_run_destroy(
        self,
        DeploymentDir,
        mock_app_builder,
        mock_app_deployer,
    ):
        # Setup mock objects
        DeploymentDir.return_value = MagicMock()
        mock_builder = MagicMock()
        mock_app_builder.return_value = mock_builder
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer

        async def destroy_and_remove_stack():
            return WorkflowJobStatus.SUCCEEDED, "reason"

        mock_deployer.destroy_and_remove_stack.side_effect = destroy_and_remove_stack

        destroy_job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                "project", WorkflowType.DESTROY.value, None, run_number=1
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id="app1",
            initiated_by="user",
        )

        # Call the method
        await run_destroy(
            destroy_job=destroy_job,
            region="region",
            assume_role_arn="arn",
            external_id="external_id",
            iac=b"iac",
            pulumi_config=self.pulumi_config,
            app_dir=self.tmp_dir / "app1",
        )

        # Assert calls
        destroy_job.refresh()
        stack = PulumiStack.get(*destroy_job.iac_stack_composite_key.split("#"))
        mock_app_builder.assert_called_once_with(Path("/tmp/app1"), None)
        mock_builder.prepare_stack.assert_called_once_with(stack)
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            "region",
            "arn",
            external_id="external_id",
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            DeploymentDir.return_value,
        )
        mock_deployer.destroy_and_remove_stack.assert_called_once_with()
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, destroy_job.status)
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, stack.status)
        self.assertEqual("reason", stack.status_reason)

    @patch("src.deployer.destroy.AppDeployer")
    @patch("src.deployer.destroy.AppBuilder")
    @patch("src.deployer.destroy.DeploymentDir")
    async def test_run_destroy_with_exception(
        self,
        DeploymentDir,
        mock_app_builder,
        mock_app_deployer,
    ):
        # Setup mock objects
        DeploymentDir.return_value = MagicMock()
        mock_builder = MagicMock()
        mock_app_builder.return_value = mock_builder
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer
        mock_deployer.destroy_and_remove_stack = AsyncMock(
            side_effect=Exception("error")
        )

        destroy_job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                "project", WorkflowType.DESTROY.value, None, run_number=1
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id="app1",
            initiated_by="user",
        )

        # Call the method
        await run_destroy(
            destroy_job=destroy_job,
            region="region",
            assume_role_arn="arn",
            external_id="external_id",
            iac=b"iac",
            pulumi_config=self.pulumi_config,
            app_dir=self.tmp_dir / "app1",
        )

        # Assert calls
        destroy_job.refresh()
        stack = PulumiStack.get(*destroy_job.iac_stack_composite_key.split("#"))
        mock_app_builder.assert_called_once_with(Path("/tmp/app1"), None)
        mock_builder.prepare_stack.assert_called_once_with(stack)
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            "region",
            "arn",
            external_id="external_id",
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            DeploymentDir.return_value,
        )
        mock_deployer.destroy_and_remove_stack.assert_called_once_with()
        self.assertEqual(WorkflowJobStatus.FAILED.value, destroy_job.status)
        self.assertEqual(WorkflowJobStatus.FAILED.value, stack.status)
        self.assertEqual("error", stack.status_reason)

    @patch("src.deployer.destroy.get_iac_storage")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_destroy_application(
        self,
        mock_run_destroy,
        mock_get_iac_storage,
    ):
        # Arrange
        mock_iac_storage = MagicMock(
            spec=IacStorage,
            get_iac=MagicMock(return_value=b"iac"),
        )
        mock_get_iac_storage.return_value = mock_iac_storage

        d_result = DeploymentResult(
            manager=None,
            status=WorkflowJobStatus.SUCCEEDED,
            reason="reason",
            stack=None,
        )

        destroy_job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                "project", WorkflowType.DESTROY.value, None, run_number=1
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id="app1",
            initiated_by="user",
        )

        def run_destroy_side_effect(*args, **kwargs):
            destroy_job.status = WorkflowJobStatus.SUCCEEDED.value
            destroy_job.save()
            return d_result

        mock_run_destroy.side_effect = run_destroy_side_effect

        request = StackDeploymentRequest(
            workflow_job=destroy_job,
            pulumi_config=self.pulumi_config,
            outputs={},
        )

        # Act
        result = await run_destroy_application(
            destroy_request=request,
            tmp_dir=self.tmp_dir,
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_iac_storage.get_iac.assert_called_once_with("project", "app1", 1)
        mock_run_destroy.assert_called_once()
        self.assertEqual(result, d_result)
        self.app1.refresh()
        destroy_job.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.app1.status)
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, destroy_job.status)

    @patch("src.deployer.destroy.get_iac_storage")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_destroy_application_no_deployed_version(
        self,
        mock_run_destroy,
        mock_get_iac_storage,
    ):
        # Arrange
        self.app1.update(
            actions=[
                AppDeployment.status.set(AppLifecycleStatus.NEW.value),
                AppDeployment.deployments.set([]),
            ]
        )

        mock_iac_storage = MagicMock(
            spec=IacStorage,
            get_iac=MagicMock(return_value=b"iac"),
        )
        mock_get_iac_storage.return_value = mock_iac_storage

        destroy_job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                "project", WorkflowType.DESTROY.value, None, run_number=1
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id="app1",
            initiated_by="user",
        )

        request = StackDeploymentRequest(
            workflow_job=destroy_job,
            pulumi_config=self.pulumi_config,
            outputs={},
        )

        # Act
        result = await run_destroy_application(
            destroy_request=request,
            tmp_dir=self.tmp_dir,
        )

        # Assert
        mock_iac_storage.get_iac.assert_not_called()
        mock_run_destroy.assert_not_called()
        self.assertEqual(WorkflowJobStatus.SUCCEEDED, result.status)
        self.app1.refresh()
        destroy_job.refresh()
        self.assertEqual(AppLifecycleStatus.NEW.value, self.app1.status)
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, destroy_job.status)

    @patch("src.deployer.destroy.get_iac_storage")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_destroy_application_no_iac(
        self,
        mock_run_destroy,
        mock_get_iac_storage,
    ):
        # Arrange
        mock_iac_storage = MagicMock(
            spec=IacStorage,
            get_iac=MagicMock(side_effect=IaCDoesNotExistError()),
        )
        mock_get_iac_storage.return_value = mock_iac_storage

        d_result = DeploymentResult(
            manager=None,
            status=WorkflowJobStatus.SUCCEEDED,
            reason="IaC does not exist",
            stack=None,
        )

        destroy_job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                "project", WorkflowType.DESTROY.value, None, run_number=1
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id="app1",
            initiated_by="user",
        )

        request = StackDeploymentRequest(
            workflow_job=destroy_job,
            pulumi_config=self.pulumi_config,
            outputs={},
        )

        # Act
        result = await run_destroy_application(
            destroy_request=request,
            tmp_dir=self.tmp_dir,
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_iac_storage.get_iac.assert_called_once_with("project", "app1", 1)
        mock_run_destroy.assert_not_called()
        self.assertEqual(result, d_result)
        self.app1.refresh()
        destroy_job.refresh()
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, self.app1.status)
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, destroy_job.status)

    @patch("src.deployer.destroy.run_destroy_application")
    @patch("src.deployer.destroy.Pool")
    async def test_run_concurrent_destroys(
        self, mock_pool, mock_run_destroy_application
    ):
        # Arrange
        app2 = AppDeployment(
            project_id="project",
            range_key=AppDeployment.compose_range_key("app2", 1),
            created_by="user",
            status=AppLifecycleStatus.INSTALLED.value,
            status_reason="reason",
            configuration={"key1": "value1"},
            deployments=["deployment1"],
        )
        app2.save()
        self.project.apps["app2"] = 1
        self.project.save()

        mock_pool_instance = mock_pool.return_value.__aenter__.return_value
        mock_pool_instance.apply = mock_run_destroy_application

        def run_destroy_application_side_effect(task, kwds):
            kwds["destroy_request"].workflow_job.update(
                actions=[WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value)]
            )
            if kwds["destroy_request"].workflow_job.modified_app_id == "app1":
                self.app1.update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.UNINSTALLED.value)
                    ]
                )
            elif kwds["destroy_request"].workflow_job.modified_app_id == "app2":
                app2.update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.UNINSTALLED.value)
                    ]
                )
            return DeploymentResult(
                manager=None,
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=None,
            )

        mock_run_destroy_application.side_effect = run_destroy_application_side_effect
        stack_deployment_requests = [
            StackDeploymentRequest(
                workflow_job=WorkflowJob.create_job(
                    partition_key=WorkflowJob.compose_partition_key(
                        "project", WorkflowType.DESTROY.value, None, run_number=1
                    ),
                    job_type=WorkflowJobType.DESTROY,
                    modified_app_id="app1",
                    initiated_by="user",
                ),
                pulumi_config=self.pulumi_config,
                outputs={},
            ),
            StackDeploymentRequest(
                workflow_job=WorkflowJob.create_job(
                    partition_key=WorkflowJob.compose_partition_key(
                        "project", WorkflowType.DESTROY.value, None, run_number=2
                    ),
                    job_type=WorkflowJobType.DESTROY,
                    modified_app_id="app2",
                    initiated_by="user",
                ),
                pulumi_config=self.pulumi_config,
                outputs={},
            ),
        ]

        # Act
        app_order, results = await run_concurrent_destroys(
            stack_deployment_requests, self.tmp_dir
        )

        # Assert
        mock_pool.assert_called_once()
        mock_pool_instance.apply.assert_has_calls(
            [
                call(
                    mock_run_destroy_application,
                    kwds={
                        "destroy_request": stack_deployment_requests[0],
                        "tmp_dir": self.tmp_dir,
                    },
                ),
                call(
                    mock_run_destroy_application,
                    kwds={
                        "destroy_request": stack_deployment_requests[1],
                        "tmp_dir": self.tmp_dir,
                    },
                ),
            ]
        )
        assert app_order == ["app1", "app2"]
        assert all(isinstance(result, DeploymentResult) for result in results)
        assert all(result.status == WorkflowJobStatus.SUCCEEDED for result in results)

        workflow_jobs = list(WorkflowJob.scan())
        self.assertEqual(2, len(workflow_jobs))
        assert all(
            job.status == WorkflowJobStatus.SUCCEEDED.value for job in workflow_jobs
        )
        self.app1.refresh()
        app2.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.app1.status)
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, app2.status)

    @patch("src.deployer.destroy.run_concurrent_destroys")
    async def test_destroy_applications(self, mock_run_concurrent_destroys):
        # Arrange
        app2 = AppDeployment(
            project_id="project",
            range_key=AppDeployment.compose_range_key("app2", 1),
            created_by="user",
            status=AppLifecycleStatus.INSTALLED.value,
            status_reason="reason",
            configuration={"key1": "value1"},
            deployments=["deployment1"],
        )
        app2.save()

        jobs = [
            WorkflowJob.create_job(
                partition_key=WorkflowJob.compose_partition_key(
                    "project", WorkflowType.DESTROY.value, None, run_number=1
                ),
                job_type=WorkflowJobType.DESTROY,
                modified_app_id="app1",
                initiated_by="user",
            ),
            WorkflowJob.create_job(
                partition_key=WorkflowJob.compose_partition_key(
                    "project", WorkflowType.DESTROY.value, None, run_number=2
                ),
                job_type=WorkflowJobType.DESTROY,
                modified_app_id="app2",
                initiated_by="user",
            ),
        ]

        def run_concurrent_destroys_side_effect(destroy_requests, tmp_dir):
            for request in destroy_requests:
                request.workflow_job.update(
                    actions=[WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value)]
                )
                if request.workflow_job.modified_app_id == "app1":
                    self.app1.update(
                        actions=[
                            AppDeployment.status.set(
                                AppLifecycleStatus.UNINSTALLED.value
                            )
                        ]
                    )
                elif request.workflow_job.modified_app_id == "app2":
                    app2.update(
                        actions=[
                            AppDeployment.status.set(
                                AppLifecycleStatus.UNINSTALLED.value
                            )
                        ]
                    )
            return (
                ["app1", "app2"],
                [
                    DeploymentResult(
                        manager=None,
                        status=WorkflowJobStatus.SUCCEEDED,
                        reason="Success",
                        stack=None,
                    ),
                    DeploymentResult(
                        manager=None,
                        status=WorkflowJobStatus.SUCCEEDED,
                        reason="Success",
                        stack=None,
                    ),
                ],
            )

        mock_run_concurrent_destroys.side_effect = run_concurrent_destroys_side_effect

        # Act
        result = await destroy_applications(jobs, self.tmp_dir)

        # Assert
        self.assertTrue(result)
        mock_run_concurrent_destroys.assert_called_once_with(
            destroy_requests=[
                StackDeploymentRequest(
                    workflow_job=jobs[0],
                    pulumi_config={},
                ),
                StackDeploymentRequest(
                    workflow_job=jobs[1],
                    pulumi_config={},
                ),
            ],
            tmp_dir=self.tmp_dir,
        )
        for job in jobs:
            job.refresh()
            self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, job.status)
        self.app1.refresh()
        app2.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.app1.status)
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, app2.status)

    @patch("src.deployer.destroy.run_concurrent_destroys")
    async def test_destroy_app(
        self,
        mock_run_concurrent_deployments,
    ):
        d_result = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=WorkflowJobStatus.SUCCEEDED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )

        def run_concurrent_destroys_side_effect(destroy_requests, tmp_dir):
            for request in destroy_requests:
                request.workflow_job.update(
                    actions=[WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value)]
                )
                if request.workflow_job.modified_app_id == "app1":
                    self.app1.update(
                        actions=[
                            AppDeployment.status.set(
                                AppLifecycleStatus.UNINSTALLED.value
                            )
                        ]
                    )
            return (
                ["app1"],
                [d_result],
            )

        mock_run_concurrent_deployments.side_effect = (
            run_concurrent_destroys_side_effect
        )

        job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                "project", WorkflowType.DESTROY.value, None, run_number=1
            ),
            job_type=WorkflowJobType.DESTROY,
            modified_app_id="app1",
            initiated_by="user",
        )

        result = await destroy_app(job, self.tmp_dir)

        self.assertEqual(result, d_result)
        mock_run_concurrent_deployments.assert_called_once_with(
            [
                StackDeploymentRequest(
                    workflow_job=job,
                    pulumi_config={},
                )
            ],
            tmp_dir=self.tmp_dir,
        )

        job.refresh()
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, job.status)
        self.app1.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.app1.status)

    @patch("src.deployer.destroy.destroy_app")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_single(
        self,
        mock_tmp_dir,
        mock_destroy_app,
    ):
        mock_tmp_dir.return_value.__enter__.return_value = Path("/tmp")

        workflow_run = WorkflowRun.create(
            project_id="project",
            workflow_type=WorkflowType.DESTROY,
            app_id=self.app1.app_id(),
            notification_email="email",
            initiated_by="user",
        )

        def tear_down_app_side_effect(destroy_job: WorkflowJob, tmp_dir: Path):
            destroy_job.update(
                actions=[WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value)]
            )
            if destroy_job.modified_app_id == "app1":
                self.app1.update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.UNINSTALLED.value)
                    ]
                )
            elif destroy_job.modified_app_id == Project.COMMON_APP_NAME:
                self.common_app.update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.UNINSTALLED.value)
                    ]
                )
            return DeploymentResult(
                manager=MagicMock(spec=AppManager),
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_destroy_app.side_effect = tear_down_app_side_effect

        # Act
        await execute_destroy_single_workflow(workflow_run, destroy_common=True)

        # Assert
        jobs = list(workflow_run.get_jobs())

        mock_tmp_dir.assert_called_once()
        mock_destroy_app.assert_has_calls(
            [
                call(jobs[0], Path("/tmp")),
                call(jobs[1], Path("/tmp")),
            ]
        )
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, jobs[0].status)
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, jobs[1].status)
        self.app1.refresh()
        self.common_app.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.app1.status)
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.common_app.status)

    @patch("src.deployer.destroy.destroy_app")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_single_failed(
        self,
        mock_tmp_dir,
        mock_destroy_app,
    ):
        mock_tmp_dir.return_value.__enter__.return_value = Path("/tmp")

        workflow_run = WorkflowRun.create(
            project_id="project",
            workflow_type=WorkflowType.DESTROY,
            app_id=self.app1.app_id(),
            notification_email="email",
            initiated_by="user",
        )

        def destroy_app_side_effect(destroy_job: WorkflowJob, tmp_dir: Path):
            if destroy_job.modified_app_id == "app1":
                destroy_job.update(
                    actions=[WorkflowJob.status.set(WorkflowJobStatus.FAILED.value)]
                )
                self.app1.update(
                    actions=[
                        AppDeployment.status.set(
                            AppLifecycleStatus.UNINSTALL_FAILED.value
                        )
                    ]
                )
                return DeploymentResult(
                    manager=MagicMock(spec=AppManager),
                    status=WorkflowJobStatus.FAILED,
                    reason="Error",
                    stack=MagicMock(spec=PulumiStack),
                )
            return DeploymentResult(
                manager=MagicMock(spec=AppManager),
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_destroy_app.side_effect = destroy_app_side_effect

        # Act
        await execute_destroy_single_workflow(workflow_run, destroy_common=True)

        # Assert
        jobs = list(workflow_run.get_jobs())
        common_job = [
            job for job in jobs if job.modified_app_id == Project.COMMON_APP_NAME
        ][0]
        app1_job = [job for job in jobs if job.modified_app_id == "app1"][0]
        mock_destroy_app.assert_called_once_with(app1_job, Path("/tmp"))
        self.assertEqual(WorkflowJobStatus.FAILED.value, app1_job.status)
        self.assertEqual(WorkflowJobStatus.CANCELED.value, common_job.status)
        self.app1.refresh()
        self.common_app.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALL_FAILED.value, self.app1.status)
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, self.common_app.status)
        workflow_run.refresh()
        self.assertEqual(WorkflowJobStatus.FAILED.value, workflow_run.status)

    @patch("src.deployer.destroy.destroy_app")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_destroy_in_progress(
        self,
        mock_tmp_dir,
        mock_tear_down_app,
    ):
        self.project.update(actions=[Project.destroy_in_progress.set(True)])

        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"

        workflow_run = WorkflowRun.create(
            project_id="project",
            workflow_type=WorkflowType.DESTROY,
            app_id=self.app1.app_id(),
            notification_email="email",
            initiated_by="user",
        )

        # Act
        await execute_destroy_single_workflow(workflow_run, destroy_common=True)

        # Assert
        jobs = list(workflow_run.get_jobs())
        mock_tear_down_app.assert_called_once()
        for job in jobs:
            self.assertEqual(WorkflowJobStatus.CANCELED.value, job.status)
        workflow_run.refresh()
        self.assertEqual(WorkflowJobStatus.FAILED.value, workflow_run.status)
        self.app1.refresh()
        self.common_app.refresh()
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, self.app1.status)
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, self.common_app.status)

    @patch("src.deployer.destroy.destroy_applications")
    @patch("src.deployer.destroy.destroy_app")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_pack(
        self,
        mock_temp_dir,
        mock_destroy_app,
        mock_destroy_applications,
    ):
        # Arrange
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = Path("/tmp")

        workflow_run = WorkflowRun.create(
            project_id=self.project.id,
            workflow_type=WorkflowType.DESTROY,
            app_id=None,
            notification_email="email",
            initiated_by="user",
        )

        def destroy_applications_side_effect(destroy_jobs, tmp_dir):
            for job in destroy_jobs:
                job.update(
                    actions=[WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value)]
                )
                if job.modified_app_id == "common":
                    self.common_app.update(
                        actions=[
                            AppDeployment.status.set(
                                AppLifecycleStatus.UNINSTALLED.value
                            )
                        ]
                    )
                if job.modified_app_id == "app1":
                    self.app1.update(
                        actions=[
                            AppDeployment.status.set(
                                AppLifecycleStatus.UNINSTALLED.value
                            )
                        ]
                    )
            return True

        mock_destroy_applications.side_effect = destroy_applications_side_effect

        def destroy_app_side_effect(destroy_job, tmp_dir):
            destroy_job.update(
                actions=[WorkflowJob.status.set(WorkflowJobStatus.SUCCEEDED.value)]
            )
            if destroy_job.modified_app_id == "common":
                self.common_app.update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.UNINSTALLED.value)
                    ]
                )
            if destroy_job.modified_app_id == "app1":
                self.app1.update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.UNINSTALLED.value)
                    ]
                )
            return DeploymentResult(
                manager=MagicMock(spec=AppManager),
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_destroy_app.side_effect = destroy_app_side_effect

        # Act
        await execute_destroy_all_workflow(workflow_run)

        # Assert
        jobs = list(workflow_run.get_jobs())
        app1_job = [job for job in jobs if job.modified_app_id == "app1"][0]
        common_job = [job for job in jobs if job.modified_app_id == "common"][0]
        mock_destroy_applications.assert_called_once_with(
            destroy_jobs=[
                app1_job,
            ],
            tmp_dir=self.tmp_dir,
        )
        mock_destroy_app.assert_called_once_with(
            destroy_job=common_job, tmp_dir=self.tmp_dir
        )
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, app1_job.status)
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, common_job.status)
        self.app1.refresh()
        self.common_app.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.app1.status)
        self.assertEqual(AppLifecycleStatus.UNINSTALLED.value, self.common_app.status)
        workflow_run.refresh()
        self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, workflow_run.status)

    @patch("src.deployer.destroy.destroy_applications")
    @patch("src.deployer.destroy.destroy_app")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_pack_app_fails(
        self,
        mock_temp_dir,
        mock_destroy_app,
        mock_destroy_applications,
    ):

        # Arrange
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"

        def destroy_applications_side_effect(destroy_jobs, tmp_dir):
            if len(destroy_jobs) == 1 and destroy_jobs[0].modified_app_id == "app1":
                destroy_jobs[0].update(
                    actions=[WorkflowJob.status.set(WorkflowJobStatus.FAILED.value)]
                )
                self.app1.update(
                    actions=[
                        AppDeployment.status.set(
                            AppLifecycleStatus.UNINSTALL_FAILED.value
                        )
                    ]
                )
            else:
                raise ValueError("Unexpected app")

        mock_destroy_applications.side_effect = destroy_applications_side_effect

        workflow_run = WorkflowRun.create(
            project_id=self.project.id,
            workflow_type=WorkflowType.DESTROY,
            app_id=None,
            notification_email="email",
            initiated_by="user",
        )

        # Act
        await execute_destroy_all_workflow(workflow_run)

        # Assert
        jobs = list(workflow_run.get_jobs())
        app1_job = [job for job in jobs if job.modified_app_id == "app1"][0]
        common_job = [job for job in jobs if job.modified_app_id == "common"][0]
        mock_destroy_applications.assert_called_once()
        mock_destroy_app.assert_not_called()
        self.assertEqual(WorkflowJobStatus.FAILED.value, app1_job.status)
        self.assertEqual(WorkflowJobStatus.CANCELED.value, common_job.status)
        self.app1.refresh()
        self.common_app.refresh()
        self.assertEqual(AppLifecycleStatus.UNINSTALL_FAILED.value, self.app1.status)
        self.assertEqual(
            AppLifecycleStatus.UNINSTALL_FAILED.value, self.common_app.status
        )
        workflow_run.refresh()
        self.assertEqual(WorkflowJobStatus.FAILED.value, workflow_run.status)
