from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiounittest

from src.deployer.deploy import (
    DeploymentResult,
    StackDeploymentRequest,
    build_and_deploy,
    build_and_deploy_application,
    deploy_app,
    deploy_applications,
    execute_deploy_single_workflow,
    execute_deployment_workflow,
    run_concurrent_deployments,
)
from src.deployer.models.pulumi_stack import PulumiStack
from src.deployer.models.workflow_job import (
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowJobType,
)
from src.deployer.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowType,
)
from src.deployer.pulumi.manager import AppManager
from src.project import Output, StackPack
from src.project.common_stack import CommonStack
from src.project.live_state import LiveState
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from src.project.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
from src.util.aws.ses import AppData
from tests.test_utils.pynamo_test import PynamoTest


class TestDeploy(PynamoTest, aiounittest.AsyncTestCase):
    models = [WorkflowRun, WorkflowJob, PulumiStack, Project, AppDeployment]

    @patch("src.deployer.deploy.AppDeployer")
    @patch("src.deployer.deploy.AppBuilder")
    @patch("src.deployer.deploy.auto.ConfigValue")
    @patch("src.deployer.deploy.DeploymentDir")
    async def test_build_and_deploy(
        self,
        DeploymentDir,
        auto_config_value,
        AppBuilder,
        mock_app_deployer,
    ):
        DeploymentDir.return_value = MagicMock()

        mock_builder = AppBuilder.return_value

        auto_config_value.side_effect = lambda v, secret=None: v
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer
        mock_deployer.deploy = AsyncMock(
            return_value=(WorkflowJobStatus.SUCCEEDED, "reason")
        )

        deployment_job = WorkflowJob(
            partition_key=WorkflowJob.compose_partition_key(
                project_id="project",
                workflow_type=WorkflowJobType.DEPLOY.value,
                owning_app_id=None,
                run_number=1,
            ),
            job_number=1,
            job_type=WorkflowJobType.DEPLOY.value,
            title="title",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            modified_app_id="app",
            initiated_by="user",
        )
        deployment_job.save()

        # Call the method
        cfg = {"key": "value"}
        await build_and_deploy(
            deployment_job=deployment_job,
            pulumi_config=cfg,
            app_dir=Path("/tmp/app"),
            assume_role_arn="arn",
            region="region",
            external_id="external_id",
        )

        # Assert calls
        AppBuilder.assert_called_once_with(Path("/tmp/app"), None)
        mock_builder.prepare_stack.assert_called_once()
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value, "region", "arn", "external_id"
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            DeploymentDir.return_value,
        )
        for k, v in cfg.items():
            mock_builder.prepare_stack.return_value.set_config.assert_called_once_with(
                k, v
            )
        mock_deployer.deploy.assert_called_once_with()

    @patch("src.deployer.deploy.AppDeployer")
    @patch("src.deployer.deploy.auto.ConfigValue")
    @patch("src.deployer.deploy.AppBuilder")
    @patch("src.deployer.deploy.DeploymentDir")
    async def test_build_and_deploy_handles_exception(
        self,
        DeploymentDir,
        AppBuilder,
        auto_config_value,
        mock_app_deployer,
    ):
        DeploymentDir.return_value = MagicMock()

        mock_builder = AppBuilder.return_value

        auto_config_value.side_effect = lambda v, secret=None: v
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer
        mock_deployer.deploy = AsyncMock(side_effect=Exception("error"))

        deployment_job = WorkflowJob(
            partition_key=WorkflowJob.compose_partition_key(
                project_id="project",
                workflow_type=WorkflowJobType.DEPLOY.value,
                owning_app_id=None,
                run_number=1,
            ),
            job_number=1,
            job_type=WorkflowJobType.DEPLOY.value,
            title="title",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            modified_app_id="app",
            initiated_by="user",
        )
        deployment_job.save()

        # Call the method
        cfg = {"key": "value"}
        result = await build_and_deploy(
            deployment_job=deployment_job,
            pulumi_config=cfg,
            app_dir=Path("/tmp/app"),
            assume_role_arn="arn",
            region="region",
        )

        # Assert calls
        pulumi_stack = PulumiStack.get(
            *PulumiStack.split_composite_key(deployment_job.iac_stack_composite_key)
        )
        self.assertEqual(WorkflowJobStatus.FAILED.value, pulumi_stack.status)
        AppBuilder.assert_called_once_with(Path("/tmp/app"), None)
        mock_builder.prepare_stack.assert_called_once_with(pulumi_stack)
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value, "region", "arn", None
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            DeploymentDir.return_value,
        )
        for k, v in cfg.items():
            mock_builder.prepare_stack.return_value.set_config.assert_called_once_with(
                k, v
            )
        mock_deployer.deploy.assert_called_once_with()

        assert result.status == WorkflowJobStatus.FAILED
        assert result.reason == "Internal error"

    @patch("src.deployer.deploy.get_binary_storage")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch("src.deployer.deploy.build_and_deploy")
    @patch("src.deployer.deploy.export_iac")
    @patch("src.deployer.deploy.get_stack_packs")
    @patch.object(AppDeployment, "run_app")
    async def test_build_and_deploy_application(
        self,
        mock_run_app,
        mock_get_stack_packs,
        mock_export_iac,
        mock_build_and_deploy,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        # Arrange
        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"app1": 1},
            created_by="user",
            owner="owner",
            features=[],
        )
        project.save()

        app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
        )
        app.save()

        mock_get_stack_packs.return_value = {
            app.app_id(): MagicMock(),
        }

        mock_iac_storage = MagicMock(spec=IacStorage, write_iac=MagicMock())
        mock_get_iac_storage.return_value = mock_iac_storage
        mock_pulumi_stack = MagicMock(
            spec=PulumiStack, composite_key=MagicMock(return_value="key")
        )
        mock_manager = MagicMock(
            spec=AppManager,
            get_outputs=MagicMock(return_value={"key1": "value1"}),
        )
        mock_build_and_deploy.return_value = DeploymentResult(
            manager=mock_manager,
            status=WorkflowJobStatus.SUCCEEDED,
            reason="Success",
            stack=mock_pulumi_stack,
        )
        outputs = {"key": "value"}

        deployment_job = WorkflowJob(
            partition_key=WorkflowJob.compose_partition_key(
                project_id="id",
                workflow_type=WorkflowJobType.DEPLOY.value,
                owning_app_id=None,
                run_number=1,
            ),
            job_number=1,
            job_type=WorkflowJobType.DEPLOY.value,
            title="title",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            modified_app_id="app1",
            initiated_by="user",
        )
        deployment_job.save()

        # Act
        result = await build_and_deploy_application(
            deployment_job=deployment_job,
            imports=[],
            pulumi_config={"key": "value"},
            outputs=outputs,
            tmp_dir=Path("/tmp"),
        )
        app.refresh()
        deployment_job.refresh()

        # Assert
        mock_run_app.assert_called_once_with(
            stack_pack=mock_get_stack_packs.return_value["app1"],
            app_dir=Path("/tmp/app1"),
            binary_storage=mock_get_binary_storage.return_value,
            imports=[],
        )
        mock_get_binary_storage.assert_called_once()
        mock_get_iac_storage.assert_called_once()
        mock_export_iac.assert_called_once()
        mock_build_and_deploy.assert_called_once_with(
            deployment_job=deployment_job,
            region=project.region,
            assume_role_arn=project.assumed_role_arn,
            pulumi_config={"key": "value"},
            app_dir=Path("/tmp/app1"),
            external_id=None,
        )

        self.assertEqual(AppLifecycleStatus.INSTALLED.value, app.status)
        self.assertEqual({"key1": "value1"}, deployment_job.outputs)
        self.assertEqual("key", app.iac_stack_composite_key)
        self.assertEqual(
            result,
            DeploymentResult(
                manager=mock_build_and_deploy.return_value.manager,
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=mock_pulumi_stack,
            ),
        )

    @patch("src.deployer.deploy.Pool")
    @patch("src.deployer.deploy.build_and_deploy_application")
    async def test_run_concurrent_deployments(
        self, mock_build_and_deploy_application, mock_pool
    ):
        mock_pool_instance = mock_pool.return_value.__aenter__.return_value
        mock_pool_instance.apply = mock_build_and_deploy_application

        expected_result = DeploymentResult(
            manager=None,
            stack=None,
            status=WorkflowJobStatus.SUCCEEDED,
            reason="Success",
        )
        mock_build_and_deploy_application.return_value = expected_result
        stack_deployment_requests = [
            StackDeploymentRequest(
                WorkflowJob(
                    partition_key=WorkflowJob.compose_partition_key(
                        project_id="project",
                        workflow_type=WorkflowJobType.DEPLOY.value,
                        owning_app_id=None,
                        run_number=1,
                    ),
                    job_number=1,
                    title="title",
                    status=WorkflowJobStatus.PENDING,
                    modified_app_id="app1",
                ),
                pulumi_config={},
                outputs={"key": "value"},
            ),
            StackDeploymentRequest(
                WorkflowJob(
                    partition_key=WorkflowJob.compose_partition_key(
                        project_id="project",
                        workflow_type=WorkflowJobType.DEPLOY.value,
                        owning_app_id=None,
                        run_number=2,
                    ),
                    job_number=2,
                    title="title",
                    status=WorkflowJobStatus.PENDING,
                    modified_app_id="app2",
                ),
                pulumi_config={},
                outputs={"key": "value2"},
            ),
        ]

        app_order, results = await run_concurrent_deployments(
            stack_deployment_requests, [], Path("/tmp")
        )

        mock_pool.assert_called_once()
        self.assertEqual(["app1", "app2"], app_order)
        self.assertEqual([expected_result, expected_result], results)

    @patch("src.deployer.deploy.get_stack_packs")
    @patch("src.deployer.deploy.run_concurrent_deployments")
    @patch("src.deployer.deploy.run_actions")
    @patch.object(AppDeployment, "get")
    @patch("src.deployer.deploy.CommonStack")
    async def test_deploy_applications(
        self,
        mock_common_stack,
        mock_get,
        mock_run_actions,
        mock_run_concurrent_deployments,
        mock_get_stack_packs,
    ):
        # Arrange
        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={"key": "value"},
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={"key2": "value2"},
        )
        app2.save()

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"app1": 1, "app2": 1, "common": 1},
            created_by="user",
            owner="owner",
        )
        project.save()

        sp1 = MagicMock(
            spec=StackPack,
            get_pulumi_configs=MagicMock(return_value={"key": "value"}),
            outputs={
                "key": Output(value="aws:res:the-cf#Domain", description="The domain")
            },
        )
        sp2 = MagicMock(
            spec=StackPack,
            get_pulumi_configs=MagicMock(return_value={"key2": "value2"}),
            outputs={
                "key": Output(value="aws:res:the-ff#DnsName", description="The domain")
            },
        )
        mock_sps = {"app1": sp1, "app2": sp2}
        mock_get_stack_packs.return_value = mock_sps
        mock_run_concurrent_deployments.side_effect = [
            (
                ["app1", "app2"],
                [
                    DeploymentResult(
                        manager=MagicMock(spec=AppManager),
                        status=WorkflowJobStatus.SUCCEEDED,
                        reason="Success",
                        stack=MagicMock(spec=PulumiStack),
                    ),
                    DeploymentResult(
                        manager=MagicMock(spec=AppManager),
                        status=WorkflowJobStatus.SUCCEEDED,
                        reason="Success",
                        stack=MagicMock(spec=PulumiStack),
                    ),
                ],
            )
        ]

        common_app = MagicMock(
            spec=AppDeployment,
        )
        mock_get.return_value = common_app
        common_stack = MagicMock(
            spec=CommonStack,
            get_pulumi_configs=MagicMock(return_value={}),
        )
        mock_common_stack.return_value = common_stack

        job1 = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                project_id="id",
                workflow_type=WorkflowJobType.DEPLOY.value,
                owning_app_id=None,
                run_number=1,
            ),
            job_type=WorkflowJobType.DEPLOY,
            modified_app_id="app1",
            title="title",
            initiated_by="user",
        )
        job2 = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                project_id="id",
                workflow_type=WorkflowJobType.DEPLOY.value,
                owning_app_id=None,
                run_number=1,
            ),
            job_type=WorkflowJobType.DEPLOY,
            modified_app_id="app2",
            title="title",
            initiated_by="user",
        )

        live_state = MagicMock(
            spec=LiveState, to_constraints=MagicMock(return_value=["constraint1"])
        )

        # Act
        result = await deploy_applications(
            deployment_jobs=[job1, job2],
            imports=[],
            tmp_dir=Path("/tmp"),
            project=project,
            live_state=live_state,
        )

        # Assert
        self.assertTrue(result)
        sp1.get_pulumi_configs.assert_called_once_with({"key": "value"})
        sp2.get_pulumi_configs.assert_called_once_with({"key2": "value2"})
        self.assertEqual(2, mock_run_actions.call_count)
        mock_run_concurrent_deployments.assert_called_once_with(
            stacks=[
                StackDeploymentRequest(
                    workflow_job=job1,
                    pulumi_config={"key": "value"},
                    outputs={"key": "the_cf_Domain"},
                ),
                StackDeploymentRequest(
                    workflow_job=job2,
                    pulumi_config={"key2": "value2"},
                    outputs={"key": "the_ff_DnsName"},
                ),
            ],
            imports=[],
            tmp_dir=Path("/tmp"),
        )

    @patch("src.deployer.deploy.run_concurrent_deployments")
    async def test_deploy_app(
        self,
        mock_run_concurrent_deployments,
    ):

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"app1": 1},
            created_by="user",
            owner="owner",
        )
        project.save()

        app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={"key": "value"},
        )
        app.save()

        sp = MagicMock(
            spec=StackPack,
            get_pulumi_configs=MagicMock(return_value={"key": "value"}),
            outputs={
                "key": Output(value="aws:res:the-cf#Domain", description="The domain")
            },
        )

        tmp_dir = Path("/tmp")

        d_result = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=WorkflowJobStatus.SUCCEEDED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )
        mock_run_concurrent_deployments.return_value = (
            ["app1"],
            [d_result],
        )

        job = WorkflowJob.create_job(
            partition_key=WorkflowJob.compose_partition_key(
                project_id="id",
                workflow_type=WorkflowJobType.DEPLOY.value,
                owning_app_id=None,
                run_number=1,
            ),
            job_type=WorkflowJobType.DEPLOY,
            modified_app_id="app1",
            title="title",
            initiated_by="user",
        )

        result = await deploy_app(job, app, sp, tmp_dir)

        self.assertEqual(result, d_result)

        sp.get_pulumi_configs.assert_called_once_with(app.get_configurations())
        mock_run_concurrent_deployments.assert_called_once_with(
            [
                StackDeploymentRequest(
                    workflow_job=job,
                    pulumi_config={"key": "value"},
                    outputs={"key": "the_cf_Domain"},
                )
            ],
            imports=[],
            tmp_dir=tmp_dir,
        )

    @patch("src.project.models.app_deployment.AppDeployment.run_app")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_binary_storage")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_deployment_success_email")
    @patch("src.deployer.deploy.get_stack_packs")
    @patch("src.deployer.deploy.run_actions")
    async def test_deploy_single(
        self,
        mock_run_actions,
        mock_get_stack_packs,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_get_binary_storage,
        mock_deploy_app,
        mock_run_app,
    ):

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={Project.COMMON_APP_NAME: 1, "app1": 1},
            created_by="user",
            owner="owner",
            features=["feature1", "feature2"],
        )
        project.save()

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
        )
        common_app.save()

        app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
            outputs={"URL": "url"},
        )
        app.save()

        email = "email"

        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_get_stack_packs.return_value = mock_sps
        common_stack = mock_common_stack.return_value
        common_stack.get_pulumi_configs.return_value = {"key": "value"}
        common_stack.get_outputs.return_value = {"key": "value"}
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        live_state = MagicMock(
            spec=LiveState, to_constraints=MagicMock(return_value=["constraint1"])
        )
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )

        def deploy_side_effect(
            deployment_job,
            app,
            stack_pack,
            tmp_dir,
            imports=[],
            pulumi_config={},
        ):
            app.status = AppLifecycleStatus.INSTALLED.value
            app.save()
            for job in workflow_run.get_jobs():
                job.status = WorkflowJobStatus.SUCCEEDED.value
                job.save()
            return DeploymentResult(
                manager=manager,
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_deploy_app.side_effect = deploy_side_effect

        workflow_run = WorkflowRun.create(
            project_id="id",
            workflow_type=WorkflowType.DEPLOY,
            app_id="app1",
            initiated_by="user",
            notification_email="email",
        )

        mock_run_app.return_value = Policy('{"Version": "2012-10-17","Statement": []}')

        # Act

        await execute_deploy_single_workflow(workflow_run)

        # Assert
        mock_get_stack_packs.assert_called_once()
        mock_common_stack.assert_has_calls(
            [call([sp1], project.features), call([sp1], [])]
        )
        mock_temp_dir.return_value.__enter__.assert_called_once()
        self.assertEqual(2, mock_deploy_app.call_count)
        mock_run_actions.assert_called_once()
        manager.read_deployed_state.assert_called_once()
        mock_get_ses_client.assert_called_once()
        mock_send_email.assert_called_once_with(
            mock_get_ses_client.return_value,
            email,
            [AppData(app_name="app1", login_url="url")],
        )

        self.assertEqual(WorkflowRunStatus.SUCCEEDED.value, workflow_run.status)
        for job in workflow_run.get_jobs():
            self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, job.status)
        app.refresh()
        common_app.refresh()
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, app.status)
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, common_app.status)

    @patch("src.project.models.app_deployment.AppDeployment.run_app")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_deployment_success_email")
    @patch("src.deployer.deploy.get_stack_packs")
    @patch("src.deployer.deploy.get_binary_storage")
    async def test_deploy_single_common_stack_fails(
        self,
        mock_get_binary_storage,
        mock_get_stack_packs,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_deploy_app,
        mock_run_app,
    ):
        mock_get_binary_storage.return_value = MagicMock()

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={Project.COMMON_APP_NAME: 1, "app1": 1},
            created_by="user",
            owner="owner",
            features=["feature1", "feature2"],
        )

        project.save()

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
        )
        common_app.save()

        app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
            outputs={"URL": "url"},
        )
        app.save()

        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_get_stack_packs.return_value = mock_sps
        common_stack = mock_common_stack.return_value
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        live_state = MagicMock(
            spec=LiveState, to_constraints=MagicMock(return_value=["constraint1"])
        )
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )

        workflow_run = WorkflowRun.create(
            project_id="id",
            workflow_type=WorkflowType.DEPLOY,
            app_id="app1",
            initiated_by="user",
            notification_email="email",
        )

        def deploy_side_effect(
            deployment_job,
            app,
            stack_pack,
            tmp_dir,
            imports=[],
        ):
            app.status = AppLifecycleStatus.UPDATE_FAILED.value
            app.save()
            for job in workflow_run.get_jobs():
                job.status = WorkflowJobStatus.FAILED.value
                job.save()
            return DeploymentResult(
                manager=None,
                status=WorkflowJobStatus.FAILED,
                reason="fail",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_deploy_app.side_effect = deploy_side_effect

        # Act
        await execute_deploy_single_workflow(workflow_run)

        mock_get_stack_packs.assert_called_once()
        mock_temp_dir.return_value.__enter__.assert_called_once()
        self.assertEqual(1, mock_deploy_app.call_count)
        manager.read_deployed_state.assert_not_called()
        mock_run_app.assert_not_called()
        mock_get_ses_client.assert_not_called()
        mock_send_email.assert_not_called()
        self.assertEqual(WorkflowRunStatus.FAILED.value, workflow_run.status)
        for job in workflow_run.get_jobs():
            self.assertEqual(WorkflowJobStatus.FAILED.value, job.status)
        app.refresh()
        common_app.refresh()
        self.assertEqual(AppLifecycleStatus.UPDATE_FAILED.value, common_app.status)
        self.assertEqual(AppLifecycleStatus.UPDATE_FAILED.value, app.status)

    @patch("src.deployer.deploy.get_stack_packs")
    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_binary_storage")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_deployment_success_email")
    async def test_deploy_project(
        self,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_get_binary_storage,
        mock_deploy_app,
        mock_deploy_applications,
        mock_get_stack_packs,
    ):
        # Arrange
        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_get_stack_packs.return_value = mock_sps
        mock_binary_storage = mock_get_binary_storage.return_value

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"common": 1, "app1": 1},
            created_by="user",
            owner="owner",
            features=["feature1", "feature2"],
        )
        project.save()

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
            outputs={"URL": "url"},
        )
        app1.save()

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("common", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
        )
        common_app.save()

        common_stack = MagicMock(spec=CommonStack)
        live_state = MagicMock(
            spec=LiveState, update=MagicMock(), transition_status=MagicMock()
        )
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )
        mock_common_stack.return_value = common_stack
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        mock_get_ses_client.return_value = MagicMock()

        workflow_run = WorkflowRun.create(
            project_id="id",
            workflow_type=WorkflowType.DEPLOY,
            app_id="app1",
            initiated_by="user",
            notification_email="email",
        )
        workflow_run.save()

        def deploy_apps_side_effect(
            deployment_jobs, imports, tmp_dir, project, live_state
        ):
            if project is None or live_state is None:
                return False
            for job in deployment_jobs:
                job.status = WorkflowJobStatus.SUCCEEDED.value
                job.save()
                AppDeployment.get_latest_version(
                    project_id=project.id, app_id=job.modified_app_id
                ).update(
                    actions=[
                        AppDeployment.status.set(AppLifecycleStatus.INSTALLED.value)
                    ]
                )
            return True

        mock_deploy_applications.side_effect = deploy_apps_side_effect

        def deploy_side_effect(
            deployment_job,
            app,
            stack_pack,
            tmp_dir,
        ):
            app.status = AppLifecycleStatus.INSTALLED.value
            app.save()
            for job in workflow_run.get_jobs():
                job.status = WorkflowJobStatus.SUCCEEDED.value
                job.save()
            return DeploymentResult(
                manager=manager,
                status=WorkflowJobStatus.SUCCEEDED,
                reason="Success",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_deploy_app.side_effect = deploy_side_effect

        # Act
        await execute_deployment_workflow(workflow_run)

        # Assert

        mock_common_stack.assert_called_once_with([sp1], project.features)
        mock_deploy_app.assert_called_once()
        mock_deploy_applications.assert_called_once()
        mock_send_email.assert_called_once_with(
            mock_get_ses_client.return_value,
            "email",
            [AppData(app_name="app1", login_url="url")],
        )
        self.assertEqual(WorkflowRunStatus.SUCCEEDED.value, workflow_run.status)
        for job in workflow_run.get_jobs():
            self.assertEqual(WorkflowJobStatus.SUCCEEDED.value, job.status)
        app1.refresh()
        common_app.refresh()
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, app1.status)
        self.assertEqual(AppLifecycleStatus.INSTALLED.value, common_app.status)

    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.send_deployment_success_email")
    async def test_deploy_pack_blocks_if_teardown_ongoing(
        self,
        mock_send_email,
        mock_common_stack,
        mock_get_iac_storage,
        mock_deploy_app,
        mock_deploy_applications,
    ):

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"common": 1, "app1": 1},
            created_by="user",
            owner="owner",
            features=["feature1", "feature2"],
            destroy_in_progress=True,
        )
        project.save()

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("common", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
        )
        common_app.save()

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
            outputs={"URL": "url"},
        )
        app1.save()

        workflow_run = WorkflowRun.create(
            project_id="id",
            workflow_type=WorkflowType.DEPLOY,
            app_id="app1",
            initiated_by="user",
            notification_email="email",
        )
        workflow_run.save()

        # Act
        with self.assertRaises(ValueError):
            await execute_deployment_workflow(workflow_run)

            # Assert
            mock_get_iac_storage.assert_called_once()
            mock_deploy_app.assert_not_called()
            mock_deploy_applications.assert_not_called()
            mock_send_email.assert_not_called()

    @patch("src.deployer.deploy.get_stack_packs")
    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_deployment_success_email")
    @patch("src.deployer.deploy.get_binary_storage")
    async def test_deploy_pack_common_stack_failed(
        self,
        mock_get_binary_storage,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_deploy_app,
        mock_deploy_applications,
        mock_get_stack_packs,
    ):
        # Arrange

        project = Project(
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"common": 1, "app1": 1},
            created_by="user",
            owner="owner",
            features=["feature1", "feature2"],
        )
        project.save()

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("common", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
        )
        common_app.save()

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user",
            status=WorkflowJobStatus.PENDING.value,
            status_reason="Deployment in progress",
            configuration={},
            outputs={"URL": "url"},
        )
        app1.save()

        mock_binary_store = MagicMock()
        mock_get_binary_storage.return_value = mock_binary_store
        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_get_stack_packs.return_value = mock_sps
        user_pack = MagicMock(
            spec=Project,
            id="id",
            apps={"common": 1, "app1": 1},
            tear_down_in_progress=False,
            features=["feature1", "feature2"],
        )
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack

        workflow_run = WorkflowRun.create(
            project_id="id",
            workflow_type=WorkflowType.DEPLOY,
            app_id="app1",
            initiated_by="user",
            notification_email="email",
        )

        def deploy_side_effect(
            deployment_job,
            app,
            stack_pack,
            tmp_dir,
            imports=[],
        ):
            AppDeployment.transition_status(
                app, WorkflowJobStatus.FAILED, WorkflowJobType.DEPLOY, "fail"
            )
            for job in workflow_run.get_jobs():
                job.status = WorkflowJobStatus.FAILED.value
                job.save()
            return DeploymentResult(
                manager=None,
                status=WorkflowJobStatus.FAILED,
                reason="Success",
                stack=MagicMock(spec=PulumiStack),
            )

        mock_deploy_app.side_effect = deploy_side_effect
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        mock_get_ses_client.return_value = MagicMock()

        # Act
        await execute_deployment_workflow(workflow_run)

        # Assert
        mock_common_stack.assert_called_once_with([sp1], user_pack.features)
        mock_deploy_app.assert_called_once()
        mock_deploy_applications.assert_not_called()
        mock_send_email.assert_not_called()
        self.assertEqual(WorkflowRunStatus.FAILED.value, workflow_run.status)
        for job in workflow_run.get_jobs():
            self.assertEqual(WorkflowJobStatus.FAILED.value, job.status)
        common_app.refresh()
        app1.refresh()
        self.assertEqual(AppLifecycleStatus.UPDATE_FAILED.value, common_app.status)
        self.assertEqual(AppLifecycleStatus.UPDATE_FAILED.value, app1.status)
