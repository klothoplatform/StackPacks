from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import aiounittest

from src.deployer.destroy import (
    DeploymentResult,
    StackDeploymentRequest,
    destroy_applications,
    run_concurrent_destroys,
    run_destroy,
    run_destroy_application,
    execute_destroy_all_workflow,
    execute_destroy_single_workflow,
    destroy_app,
)
from src.deployer.models.deployment import (
    DeploymentAction,
    DeploymentStatus,
    PulumiStack,
)
from src.deployer.pulumi.manager import AppManager
from src.project.models.app_deployment import AppLifecycleStatus, AppDeployment
from src.project.models.project import Project
from src.project.storage.iac_storage import IaCDoesNotExistError, IacStorage


class TestDestroy(aiounittest.AsyncTestCase):
    @patch("src.deployer.destroy.AppDeployer")
    @patch("src.deployer.destroy.AppBuilder")
    @patch("src.deployer.destroy.Deployment")
    @patch("src.deployer.destroy.PulumiStack")
    @patch("src.deployer.destroy.DeploymentDir")
    async def test_run_destroy(
        self,
        DeploymentDir,
        mock_pulumi_stack,
        mock_deployment,
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
            return_value=(MagicMock(), "reason")
        )

        cfg = {}

        # Call the method
        await run_destroy(
            "region",
            "arn",
            "project",
            "app",
            "user",
            b"iac",
            cfg,
            "deploy_id",
            Path("/tmp"),
        )

        # Assert calls
        mock_pulumi_stack.assert_called_once_with(
            project_name="project",
            name=mock_pulumi_stack.sanitize_stack_name.return_value,
            status="IN_PROGRESS",
            status_reason="Destroy in progress",
            created_by="user",
        )
        mock_deployment.assert_called_once_with(
            id=ANY,
            iac_stack_composite_key=mock_pulumi_stack.return_value.create_hash_key.return_value,
            action="DESTROY",
            status="IN_PROGRESS",
            status_reason="Destroy in progress",
            initiated_by="user",
        )
        mock_app_builder.assert_called_once_with(Path("/tmp"))
        mock_builder.prepare_stack.assert_called_once_with(
            b"iac", mock_pulumi_stack.return_value
        )
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value, "arn", "region"
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            DeploymentDir.return_value,
        )
        mock_deployer.destroy_and_remove_stack.assert_called_once_with()
        mock_pulumi_stack.return_value.update.assert_called_once_with(
            actions=[
                mock_pulumi_stack.status.set(DeploymentStatus.SUCCEEDED.value),
                mock_pulumi_stack.status_reason.set("reason"),
            ]
        )
        mock_deployment.return_value.update.assert_called_once_with(
            actions=[
                mock_deployment.status.set(DeploymentStatus.SUCCEEDED.value),
                mock_deployment.status_reason.set("reason"),
            ]
        )

    @patch("src.deployer.destroy.AppDeployer")
    @patch("src.deployer.destroy.AppBuilder")
    @patch("src.deployer.destroy.Deployment")
    @patch("src.deployer.destroy.PulumiStack")
    @patch("src.deployer.destroy.DeploymentDir")
    async def test_run_destroy_with_exception(
        self,
        DeploymentDir,
        mock_pulumi_stack,
        mock_deployment,
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

        cfg = {}

        # Call the method
        result = await run_destroy(
            "region",
            "arn",
            "project",
            "app",
            "user",
            b"iac",
            cfg,
            "deploy_id",
            Path("/tmp"),
        )

        # Assert calls
        mock_pulumi_stack.assert_called_once_with(
            project_name="project",
            name=mock_pulumi_stack.sanitize_stack_name.return_value,
            status="IN_PROGRESS",
            status_reason="Destroy in progress",
            created_by="user",
        )
        mock_deployment.assert_called_once_with(
            id=ANY,
            iac_stack_composite_key=mock_pulumi_stack.return_value.create_hash_key.return_value,
            action="DESTROY",
            status="IN_PROGRESS",
            status_reason="Destroy in progress",
            initiated_by="user",
        )
        mock_app_builder.assert_called_once_with(Path("/tmp"))
        mock_builder.prepare_stack.assert_called_once_with(
            b"iac", mock_pulumi_stack.return_value
        )
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value, "arn", "region"
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value,
            DeploymentDir.return_value,
        )
        mock_deployer.destroy_and_remove_stack.assert_called_once_with()
        mock_pulumi_stack.return_value.update.assert_called_once_with(
            actions=[
                mock_pulumi_stack.status.set(DeploymentStatus.FAILED.value),
                mock_pulumi_stack.status_reason.set("error"),
            ]
        )
        mock_deployment.return_value.update.assert_called_once_with(
            actions=[
                mock_deployment.status.set(DeploymentStatus.FAILED.value),
                mock_deployment.status_reason.set("error"),
            ]
        )
        assert result.status == DeploymentStatus.FAILED
        assert result.reason == "error"

    @patch("src.deployer.destroy.get_iac_storage")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(Project, "get")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_destroy_application(
        self,
        mock_run_destroy,
        mock_user_pack_get,
        mock_user_app_get_latest_deployed_version,
        mock_get_iac_storage,
    ):
        # Arrange
        mock_iac_storage = MagicMock(
            spec=IacStorage,
            get_iac=MagicMock(return_value=b"iac"),
        )
        mock_get_iac_storage.return_value = mock_iac_storage
        mock_user_pack = MagicMock(
            spec=Project,
            region="region",
            assumed_role_arn="arn",
            id="project",
        )
        mock_user_pack_get.return_value = mock_user_pack
        mock_app = MagicMock(
            spec=AppDeployment, get_app_name=MagicMock(return_value="app"), version=1
        )
        mock_user_app_get_latest_deployed_version.return_value = mock_app
        d_result = DeploymentResult(
            manager=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="reason",
            stack=None,
        )
        mock_run_destroy.return_value = d_result

        # Act
        result = await run_destroy_application(
            "project", "app", "user", {}, "deploy_id", Path("/tmp")
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack_get.assert_called_once_with("project")
        mock_user_app_get_latest_deployed_version.assert_called_once_with("project#app")
        mock_iac_storage.get_iac.assert_called_once_with("project", "app", 1)
        mock_run_destroy.assert_called_once_with(
            "region",
            "arn",
            "project",
            "app",
            "user",
            b"iac",
            {},
            "deploy_id",
            Path("/tmp/app"),
        )
        self.assertEqual(
            mock_app.transition_status.mock_calls,
            [
                call(
                    DeploymentStatus.IN_PROGRESS,
                    DeploymentAction.DESTROY,
                    "Destroy in progress",
                ),
                call(DeploymentStatus.SUCCEEDED, DeploymentAction.DESTROY, "reason"),
            ],
        )
        mock_app.update.assert_called_once_with(
            actions=[
                AppDeployment.outputs.set({}),
                AppDeployment.iac_stack_composite_key.set(None),
                AppDeployment.deployments.add({"deploy_id"}),
            ]
        )
        self.assertEqual(result, d_result)

    @patch("src.deployer.destroy.get_iac_storage")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(Project, "get")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_destroy_application_no_deployed_version(
        self,
        mock_run_destroy,
        mock_user_pack_get,
        mock_user_app_get_latest_deployed_version,
        mock_get_iac_storage,
    ):
        # Arrange
        mock_iac_storage = MagicMock(
            spec=IacStorage,
            get_iac=MagicMock(return_value=b"iac"),
        )
        mock_get_iac_storage.return_value = mock_iac_storage
        mock_user_pack = MagicMock(
            spec=Project,
            region="region",
            assumed_role_arn="arn",
            id="project",
        )
        mock_user_pack_get.return_value = mock_user_pack
        mock_app = MagicMock(
            spec=AppDeployment, get_app_name=MagicMock(return_value="app"), version=1
        )
        mock_user_app_get_latest_deployed_version.return_value = None
        d_result = DeploymentResult(
            manager=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="Not deployed",
            stack=None,
        )

        # Act
        result = await run_destroy_application(
            "project", "app", "user", {}, "deploy_id", Path("/tmp")
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack_get.assert_called_once_with("project")
        mock_user_app_get_latest_deployed_version.assert_called_once_with("project#app")
        mock_iac_storage.get_iac.assert_not_called()
        mock_run_destroy.assert_not_called()
        mock_app.transition_status.assert_not_called()
        mock_app.update.assert_not_called()
        self.assertEqual(result, d_result)

    @patch("src.deployer.destroy.get_iac_storage")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(Project, "get")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_destroy_application_no_iac(
        self,
        mock_run_destroy,
        mock_user_pack_get,
        mock_user_app_get_latest_deployed_version,
        mock_get_iac_storage,
    ):
        # Arrange
        mock_iac_storage = MagicMock(
            spec=IacStorage,
            get_iac=MagicMock(side_effect=IaCDoesNotExistError()),
        )
        mock_get_iac_storage.return_value = mock_iac_storage
        mock_user_pack = MagicMock(
            spec=Project,
            region="region",
            assumed_role_arn="arn",
            id="project",
        )
        mock_user_pack_get.return_value = mock_user_pack
        mock_app = MagicMock(
            spec=AppDeployment, get_app_name=MagicMock(return_value="app"), version=1
        )
        mock_user_app_get_latest_deployed_version.return_value = mock_app
        d_result = DeploymentResult(
            manager=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="IaC does not exist",
            stack=None,
        )

        # Act
        result = await run_destroy_application(
            "project", "app", "user", {}, "deploy_id", Path("/tmp")
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack_get.assert_called_once_with("project")
        mock_user_app_get_latest_deployed_version.assert_called_once_with("project#app")
        mock_iac_storage.get_iac.assert_called_once_with("project", "app", 1)
        mock_run_destroy.assert_not_called()
        mock_app.transition_status.assert_not_called()
        mock_app.update.assert_not_called()
        self.assertEqual(result, d_result)

    @patch("src.deployer.destroy.Pool")
    @patch("src.deployer.destroy.run_destroy_application")
    async def test_run_concurrent_destroys(
        self, mock_run_destroy_application, mock_pool
    ):
        # Arrange
        mock_pool_instance = mock_pool.return_value.__aenter__.return_value
        mock_pool_instance.apply = mock_run_destroy_application
        mock_run_destroy_application.return_value = DeploymentResult(
            manager=None,
            stack=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
        )
        stack_deployment_requests = [
            StackDeploymentRequest(
                project_name="project",
                stack_name="stack1",
                pulumi_config={},
                deployment_id="deploy_id",
            ),
            StackDeploymentRequest(
                project_name="project",
                stack_name="stack2",
                pulumi_config={},
                deployment_id="deploy_id",
            ),
        ]

        # Act
        app_order, results = await run_concurrent_destroys(
            stack_deployment_requests, "user", Path("/tmp")
        )

        # Assert
        mock_pool.assert_called_once()
        mock_pool_instance.apply.assert_has_calls(
            [
                call(
                    mock_run_destroy_application,
                    args=(
                        "project",
                        "stack1",
                        "user",
                        {},
                        "deploy_id",
                        Path("/tmp"),
                    ),
                ),
                call(
                    mock_run_destroy_application,
                    args=(
                        "project",
                        "stack2",
                        "user",
                        {},
                        "deploy_id",
                        Path("/tmp"),
                    ),
                ),
            ]
        )
        assert app_order == ["stack1", "stack2"]
        assert all(isinstance(result, DeploymentResult) for result in results)
        assert all(result.status == DeploymentStatus.SUCCEEDED for result in results)

    @patch("src.deployer.destroy.run_concurrent_destroys")
    async def test_destroy_applications(self, mock_run_concurrent_destroys):
        # Arrange
        mock_user_pack = MagicMock(spec=Project, id="id", apps={"app1": 1, "app2": 1})
        mock_run_concurrent_destroys.side_effect = [
            (
                ["app1", "app2"],
                [
                    DeploymentResult(
                        manager=MagicMock(spec=AppManager),
                        status=DeploymentStatus.SUCCEEDED,
                        reason="Success",
                        stack=MagicMock(spec=PulumiStack),
                    ),
                    DeploymentResult(
                        manager=MagicMock(spec=AppManager),
                        status=DeploymentStatus.SUCCEEDED,
                        reason="Success",
                        stack=MagicMock(spec=PulumiStack),
                    ),
                ],
            )
        ]
        # Act
        result = await destroy_applications(mock_user_pack, "deploy_id", Path("/tmp"))

        # Assert
        self.assertTrue(result)
        mock_run_concurrent_destroys.assert_called_once_with(
            [
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app1",
                    pulumi_config={},
                    deployment_id="deploy_id",
                ),
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app2",
                    pulumi_config={},
                    deployment_id="deploy_id",
                ),
            ],
            mock_user_pack.id,
            Path("/tmp"),
        )

    @patch("src.deployer.destroy.run_concurrent_destroys")
    async def test_tear_down_user_app(
        self,
        mock_run_concurrent_deployments,
    ):
        pack = MagicMock(spec=Project, id="id", apps={"common": 1})
        app = MagicMock(
            spec=AppDeployment, get_app_name=MagicMock(return_value="app1"), version=1
        )
        deployment_id = "deployment_id"
        tmp_dir = Path("/tmp")
        d_result = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )
        mock_run_concurrent_deployments.return_value = (
            ["app1"],
            [d_result],
        )

        result = await destroy_app(pack, app, deployment_id, tmp_dir)

        self.assertEqual(result, d_result)
        mock_run_concurrent_deployments.assert_called_once_with(
            [
                StackDeploymentRequest(
                    project_name=pack.id,
                    stack_name=app.get_app_name.return_value,
                    pulumi_config={},
                    deployment_id=deployment_id,
                )
            ],
            pack.id,
            tmp_dir,
        )

    @patch("src.deployer.destroy.tear_down_user_app")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_single(
        self,
        mock_tmp_dir,
        mock_get_latest_deployed_version,
        mock_tear_down_app,
    ):
        pack = MagicMock(spec=Project, id="id", tear_down_in_progress=True)
        app = MagicMock(spec=AppDeployment, app_id="id#app", version=1)
        deployment_id = "deployment_id"
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        common_app = mock_get_latest_deployed_version.return_value
        mock_tear_down_app.return_value = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )

        await execute_destroy_single_workflow(pack, app, deployment_id)

        mock_tmp_dir.assert_called_once()
        self.assertEqual(
            mock_tear_down_app.mock_calls,
            [
                call(pack, app, deployment_id, Path("/tmp")),
                call(pack, common_app, deployment_id, Path("/tmp")),
            ],
        )
        mock_get_latest_deployed_version.assert_called_once_with("id#common")
        pack.update.assert_called_once_with(
            actions=[Project.destroy_in_progress.set(False)]
        )

    @patch("src.deployer.destroy.tear_down_user_app")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_single_failed_common_stack(
        self,
        mock_tmp_dir,
        mock_get_latest_deployed_version,
        mock_tear_down_app,
    ):
        pack = MagicMock(spec=Project, id="id", tear_down_in_progress=True)
        app = MagicMock(spec=AppDeployment, app_id="id#app", version=1)
        deployment_id = "deployment_id"
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        mock_tear_down_app.return_value = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=DeploymentStatus.FAILED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )

        await execute_destroy_single_workflow(pack, app, deployment_id)

        mock_tmp_dir.assert_called_once()
        self.assertEqual(
            mock_tear_down_app.mock_calls,
            [
                call(pack, app, deployment_id, Path("/tmp")),
            ],
        )
        mock_get_latest_deployed_version.assert_not_called()
        pack.update.assert_not_called()

    @patch("src.deployer.destroy.tear_down_user_app")
    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_single_no_pack_teardown(
        self,
        mock_tmp_dir,
        mock_get_latest_deployed_version,
        mock_tear_down_app,
    ):
        pack = MagicMock(spec=Project, id="id", tear_down_in_progress=False)
        app = MagicMock(spec=AppDeployment, app_id="id#app", version=1)
        deployment_id = "deployment_id"
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        mock_tear_down_app.return_value = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=DeploymentStatus.FAILED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )

        await execute_destroy_single_workflow(pack, app, deployment_id)

        mock_tmp_dir.assert_called_once()
        self.assertEqual(
            mock_tear_down_app.mock_calls,
            [
                call(pack, app, deployment_id, Path("/tmp")),
            ],
        )
        mock_get_latest_deployed_version.assert_not_called()
        pack.update.assert_not_called()

    @patch("src.deployer.destroy.destroy_applications")
    @patch("src.deployer.destroy.tear_down_user_app")
    @patch("src.deployer.destroy.Project")
    @patch("src.deployer.destroy.UserApp")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_pack(
        self,
        mock_temp_dir,
        mock_user_app,
        mock_user_pack,
        mock_tear_down_user_app,
        mock_destroy_applications,
    ):
        mock_user_pack.COMMON_APP_NAME = Project.COMMON_APP_NAME
        mock_user_app.create_hash_key = lambda a, b: f"{a}#{b}"
        # Arrange
        user_pack = MagicMock(spec=Project, id="id", apps={"common": 1})
        mock_user_pack.get.return_value = user_pack
        mock_common_pack = MagicMock(spec=AppDeployment)
        mock_user_app.get.return_value = mock_common_pack
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"

        # Act
        await execute_destroy_all_workflow(pack_id="id", deployment_id="deploy_id")

        # Assert
        mock_common_pack.update.assert_called_once_with(
            actions=[
                mock_user_app.status.set(AppLifecycleStatus.PENDING.value),
                mock_user_app.status_reason.set(
                    "waiting for applications to be destroyed"
                ),
            ]
        )
        mock_destroy_applications.assert_called_once_with(
            user_pack, "deploy_id", Path("/tmp")
        )
        mock_user_pack.get.assert_called_once_with("id")
        mock_user_app.get.assert_called_once_with("id#common", 1)
        mock_tear_down_user_app.assert_called_once_with(
            user_pack,
            mock_common_pack,
            "deploy_id",
            Path("/tmp"),
        )
        user_pack.update.calls = [
            call(actions=[user_pack.tear_down_in_progress.set(True)]),
            call(actions=[user_pack.tear_down_in_progress.set(False)]),
        ]

    @patch("src.deployer.destroy.destroy_applications")
    @patch("src.deployer.destroy.tear_down_user_app")
    @patch("src.deployer.destroy.Project")
    @patch("src.deployer.destroy.UserApp")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_pack_app_fails(
        self,
        mock_temp_dir,
        mock_user_app,
        mock_user_pack,
        mock_tear_down_user_app,
        mock_destroy_applications,
    ):
        mock_user_pack.COMMON_APP_NAME = Project.COMMON_APP_NAME
        mock_user_app.create_hash_key = lambda a, b: f"{a}#{b}"
        # Arrange
        user_pack = MagicMock(spec=Project, id="id", apps={"common": 1})
        mock_user_pack.get.return_value = user_pack
        mock_common_pack = MagicMock(spec=AppDeployment)
        mock_user_app.get.return_value = mock_common_pack
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        mock_destroy_applications.return_value = False
        # Act
        await execute_destroy_all_workflow(pack_id="id", deployment_id="deploy_id")

        # Assert
        mock_common_pack.update.assert_called_once_with(
            actions=[
                mock_user_app.status.set(AppLifecycleStatus.PENDING.value),
                mock_user_app.status_reason.set(
                    "waiting for applications to be destroyed"
                ),
            ]
        )
        mock_destroy_applications.assert_called_once_with(
            user_pack, "deploy_id", Path("/tmp")
        )
        mock_user_pack.get.assert_called_once_with("id")
        mock_user_app.get.assert_called_once_with("id#common", 1)
        mock_common_pack.transition_status.assert_called_once_with(
            DeploymentStatus.FAILED,
            DeploymentAction.DESTROY,
            "One or more applications failed to destroy",
        )
        mock_tear_down_user_app.assert_not_called()
