from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, call, patch

import aiounittest

from src.deployer.destroy import (
    DeploymentResult,
    StackDeploymentRequest,
    destroy_applications,
    destroy_common_stack,
    run_concurrent_destroys,
    run_destroy,
    tear_down_pack,
    tear_down_single,
    tear_down_user_app,
)
from src.deployer.models.deployment import DeploymentStatus, PulumiStack
from src.deployer.pulumi.manager import AppManager
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.storage.iac_storage import IacStorage


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
            iac_stack_composite_key=mock_pulumi_stack.return_value.composite_key.return_value,
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
        mock_pulumi_stack.return_value.update.assert_called_once()
        mock_deployment.return_value.update.assert_called_once()

    @patch("src.deployer.destroy.Pool")
    @patch("src.deployer.destroy.run_destroy")
    async def test_run_concurrent_destroys(self, mock_run_destroy, mock_pool):
        # Arrange
        mock_pool_instance = mock_pool.return_value.__aenter__.return_value
        mock_pool_instance.apply = mock_run_destroy
        mock_run_destroy.return_value = DeploymentResult(
            manager=None,
            stack=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
        )
        stack_deployment_requests = [
            StackDeploymentRequest(
                project_name="project",
                stack_name="stack1",
                iac=b"iac1",
                pulumi_config={},
                deployment_id="deploy_id",
            ),
            StackDeploymentRequest(
                project_name="project",
                stack_name="stack2",
                iac=b"iac2",
                pulumi_config={},
                deployment_id="deploy_id",
            ),
        ]

        # Act
        app_order, results = await run_concurrent_destroys(
            "region", "arn", stack_deployment_requests, "user", Path("/tmp")
        )

        # Assert
        mock_pool.assert_called_once()
        mock_pool_instance.apply.assert_has_calls(
            [
                call(
                    mock_run_destroy,
                    args=(
                        "region",
                        "arn",
                        "project",
                        "stack1",
                        "user",
                        b"iac1",
                        {},
                        "deploy_id",
                        Path("/tmp") / "stack1",
                    ),
                ),
                call(
                    mock_run_destroy,
                    args=(
                        "region",
                        "arn",
                        "project",
                        "stack2",
                        "user",
                        b"iac2",
                        {},
                        "deploy_id",
                        Path("/tmp") / "stack2",
                    ),
                ),
            ]
        )
        assert mock_run_destroy.call_count == 2
        assert app_order == ["stack1", "stack2"]
        assert all(isinstance(result, DeploymentResult) for result in results)
        assert all(result.status == DeploymentStatus.SUCCEEDED for result in results)

    @patch("src.deployer.destroy.run_concurrent_destroys")
    async def test_destroy_common_stack(self, mock_run_concurrent_destroys):
        # Arrange
        mock_user_pack = MagicMock(spec=UserPack, id="id")
        mock_common_pack = MagicMock(
            spec=UserApp,
            app_id="id#common",
            version="1",
            get_pack_id=MagicMock(return_value="id"),
            get_app_name=MagicMock(return_value="app1"),
            configuration={"key": "value"},
        )
        mock_pulumi_stack = MagicMock(spec=PulumiStack)
        mock_iac_storage = MagicMock(spec=IacStorage, get_iac=Mock(return_value=b"iac"))
        mock_manager = MagicMock()
        mock_run_concurrent_destroys.return_value = (
            ["common"],
            [
                DeploymentResult(
                    manager=mock_manager,
                    status=DeploymentStatus.SUCCEEDED,
                    reason="Success",
                    stack=mock_pulumi_stack,
                )
            ],
        )

        # Act
        await destroy_common_stack(
            mock_user_pack,
            mock_common_pack,
            mock_iac_storage,
            "deploy_id",
            Path("/tmp"),
        )

        # Assert
        mock_iac_storage.get_iac.assert_called_once_with(
            mock_user_pack.id, mock_common_pack.get_app_name(), mock_common_pack.version
        )
        mock_run_concurrent_destroys.assert_called_once_with(
            mock_user_pack.region,
            mock_user_pack.assumed_role_arn,
            [
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app1",
                    iac=b"iac",
                    pulumi_config={},
                    deployment_id="deploy_id",
                )
            ],
            mock_user_pack.id,
            Path("/tmp"),
        )
        mock_common_pack.update.assert_called_once_with(
            actions=[
                UserApp.status.set(DeploymentStatus.SUCCEEDED.value),
                UserApp.status_reason.set("Success"),
                UserApp.iac_stack_composite_key.set(None),
            ]
        )

    @patch("src.deployer.destroy.run_concurrent_destroys")
    @patch("src.deployer.destroy.UserApp")
    async def test_destroy_applications(
        self, mock_user_app, mock_run_concurrent_destroys
    ):
        # Arrange
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        mock_app_1 = MagicMock(
            spec=UserApp,
            app_id="id#app1",
            get_pack_id=MagicMock(return_value="id"),
            get_app_name=MagicMock(return_value="app1"),
            composite_key=MagicMock(return_value="id#app1"),
        )
        mock_app_2 = MagicMock(
            spec=UserApp,
            app_id="id#app2",
            get_pack_id=MagicMock(return_value="id"),
            get_app_name=MagicMock(return_value="app2"),
            composite_key=MagicMock(return_value="id#app2"),
        )
        mock_user_app.get_latest_version_with_status.side_effect = [
            mock_app_1,
            mock_app_2,
        ]
        mock_user_pack = MagicMock(spec=UserPack, id="id", apps={"app1": 1, "app2": 1})
        mock_iac_storage = MagicMock(
            spec=IacStorage, get_iac=Mock(side_effect=[b"iac1", b"iac2"])
        )
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
        await destroy_applications(
            mock_user_pack, mock_iac_storage, "deploy_id", Path("/tmp")
        )

        # Assert
        mock_user_app.get_latest_version_with_status.assert_has_calls(
            [call("id#app1"), call("id#app2")]
        )
        mock_iac_storage.get_iac.assert_has_calls(
            [call("id", "app1", 1), call("id", "app2", 1)]
        )
        mock_run_concurrent_destroys.assert_called_once_with(
            mock_user_pack.region,
            mock_user_pack.assumed_role_arn,
            [
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app1",
                    iac=b"iac1",
                    pulumi_config={},
                    deployment_id="deploy_id",
                ),
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app2",
                    iac=b"iac2",
                    pulumi_config={},
                    deployment_id="deploy_id",
                ),
            ],
            mock_user_pack.id,
            Path("/tmp"),
        )
        mock_app_1.update.assert_called_once_with(
            actions=[
                mock_user_app.status.set(DeploymentStatus.SUCCEEDED.value),
                mock_user_app.status_reason.set("Success"),
                mock_user_app.iac_stack_composite_key.set(
                    mock_run_concurrent_destroys.return_value[1][
                        0
                    ].stack.composite_key.return_value
                ),
            ]
        )
        mock_app_2.update.assert_called_once_with(
            actions=[
                mock_user_app.status.set(DeploymentStatus.SUCCEEDED.value),
                mock_user_app.status_reason.set("Success"),
                mock_user_app.iac_stack_composite_key.set(
                    mock_run_concurrent_destroys.return_value[1][
                        0
                    ].stack.composite_key.return_value
                ),
            ]
        )

    @patch("src.deployer.destroy.run_concurrent_destroys")
    async def test_tear_down_app(
        self,
        mock_run_concurrent_deployments,
    ):
        pack = MagicMock(spec=UserPack, id="id", apps={"common": 1})
        app = MagicMock(
            spec=UserApp, get_app_name=MagicMock(return_value="app1"), version=1
        )
        iac_storage = MagicMock(spec=IacStorage)
        deployment_id = "deployment_id"
        tmp_dir = Path("/tmp")
        iac_storage.get_iac.return_value = b"iac"

        mock_run_concurrent_deployments.return_value = (
            ["app1"],
            [
                DeploymentResult(
                    manager=MagicMock(spec=AppManager),
                    status=DeploymentStatus.SUCCEEDED,
                    reason="Success",
                    stack=MagicMock(spec=PulumiStack),
                )
            ],
        )

        await tear_down_user_app(pack, app, iac_storage, deployment_id, tmp_dir)

        iac_storage.get_iac.assert_called_once_with(
            pack.id, app.get_app_name(), app.version
        )
        mock_run_concurrent_deployments.assert_called_once_with(
            pack.region,
            pack.assumed_role_arn,
            [
                StackDeploymentRequest(
                    project_name=pack.id,
                    stack_name=app.get_app_name.return_value,
                    iac=iac_storage.get_iac.return_value,
                    pulumi_config={},
                    deployment_id=deployment_id,
                )
            ],
            pack.id,
            tmp_dir,
        )
        app.update.assert_called_once_with(
            actions=[
                UserApp.status.set(DeploymentStatus.SUCCEEDED.value),
                UserApp.status_reason.set("Success"),
                UserApp.iac_stack_composite_key.set(None),
            ]
        )

    @patch("src.deployer.destroy.get_iac_storage")
    @patch("src.deployer.destroy.tear_down_user_app")
    @patch.object(UserApp, "get_latest_version_with_status")
    @patch("src.deployer.destroy.destroy_common_stack")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_single(
        self,
        mock_tmp_dir,
        mock_destroy_common_stack,
        mock_get_latest_version_with_status,
        mock_tear_down_app,
        mock_get_iac_storage,
    ):
        pack = MagicMock(spec=UserPack, id="id")
        app = MagicMock(spec=UserApp, app_id="id#app", version=1)
        deployment_id = "deployment_id"
        iac_storage = mock_get_iac_storage.return_value
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        common_app = mock_get_latest_version_with_status.return_value

        await tear_down_single(pack, app, deployment_id)

        mock_get_iac_storage.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tear_down_app.assert_called_once_with(
            pack, app, iac_storage, deployment_id, Path("/tmp")
        )
        mock_get_latest_version_with_status.assert_called_once_with("id#common")
        mock_destroy_common_stack.assert_called_once_with(
            pack, common_app, iac_storage, deployment_id, Path("/tmp")
        )
        pack.update.assert_called_once_with(
            actions=[UserPack.tear_down_in_progress.set(False)]
        )

    @patch("src.deployer.destroy.destroy_applications")
    @patch("src.deployer.destroy.destroy_common_stack")
    @patch("src.deployer.destroy.get_iac_storage")
    @patch("src.deployer.destroy.UserPack")
    @patch("src.deployer.destroy.UserApp")
    @patch("src.deployer.destroy.TempDir")
    async def test_tear_down_pack(
        self,
        mock_temp_dir,
        mock_user_app,
        mock_user_pack,
        mock_get_iac_storage,
        mock_destroy_common_stack,
        mock_destroy_applications,
    ):
        mock_user_pack.COMMON_APP_NAME = UserPack.COMMON_APP_NAME
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        # Arrange
        mock_iac_storage = mock_get_iac_storage.return_value
        user_pack = MagicMock(spec=UserPack, id="id", apps={"common": 1})
        mock_user_pack.get.return_value = user_pack
        mock_common_pack = MagicMock(spec=UserApp)
        mock_user_app.get.return_value = mock_common_pack
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"

        # Act
        await tear_down_pack(pack_id="id", deployment_id="deploy_id")

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_destroy_applications.assert_called_once_with(
            user_pack, mock_iac_storage, "deploy_id", Path("/tmp")
        )
        mock_user_pack.get.assert_called_once_with("id")
        mock_user_app.get.assert_called_once_with("id#common", 1)
        mock_destroy_common_stack.assert_called_once_with(
            user_pack,
            mock_common_pack,
            mock_iac_storage,
            "deploy_id",
            Path("/tmp"),
        )
        user_pack.update.calls = [
            call(actions=[user_pack.tear_down_in_progress.set(True)]),
            call(actions=[user_pack.tear_down_in_progress.set(False)]),
        ]
