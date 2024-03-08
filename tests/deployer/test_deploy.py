from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, call, patch

import aiounittest

from src.deployer.deploy import (
    DeploymentResult,
    StackDeploymentRequest,
    build_and_deploy,
    deploy_applications,
    deploy_common_stack,
    deploy_pack,
    rerun_pack_with_live_state,
    run_concurrent_deployments,
)
from src.deployer.models.deployment import DeploymentStatus, PulumiStack
from src.deployer.pulumi.manager import AppManager
from src.stack_pack import StackPack
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.live_state import LiveState
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.storage.iac_storage import IacStorage


class TestDeploy(aiounittest.AsyncTestCase):
    @patch("src.deployer.deploy.AppDeployer")
    @patch("src.deployer.deploy.Deployment")
    @patch("src.deployer.deploy.PulumiStack")
    @patch("src.deployer.deploy.AppBuilder")
    @patch("src.deployer.deploy.auto.ConfigValue")
    @patch("src.deployer.deploy.DeploymentDir")
    async def test_build_and_deploy(
        self,
        DeploymentDir,
        auto_config_value,
        AppBuilder,
        mock_pulumi_stack,
        mock_deployment,
        mock_app_deployer,
    ):
        DeploymentDir.return_value = MagicMock()

        mock_builder = AppBuilder.return_value

        auto_config_value.side_effect = lambda v, secret: v
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer
        mock_deployer.deploy = AsyncMock(return_value=(MagicMock(), "reason"))

        # Call the method
        cfg = {"key": "value"}
        await build_and_deploy(
            "region", "arn", "app", "user", b"iac", cfg, "deploy_id", Path("/tmp")
        )

        # Assert calls
        mock_pulumi_stack.assert_called_once_with(
            project_name="StackPack",
            name=mock_pulumi_stack.sanitize_stack_name.return_value,
            status="IN_PROGRESS",
            status_reason="Deployment in progress",
            created_by="user",
        )
        mock_deployment.assert_called_once_with(
            id=ANY,
            iac_stack_composite_key=mock_pulumi_stack.return_value.composite_key.return_value,
            action="DEPLOY",
            status="IN_PROGRESS",
            status_reason="Deployment in progress",
            initiated_by="user",
        )
        AppBuilder.assert_called_once_with(Path("/tmp"))
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
        for k, v in cfg.items():
            mock_builder.prepare_stack.return_value.set_config.assert_called_once_with(
                k, v
            )
        mock_deployer.deploy.assert_called_once_with()
        mock_pulumi_stack.return_value.update.assert_called_once()
        mock_deployment.return_value.update.assert_called_once()

    @patch("src.deployer.deploy.Pool")
    @patch("src.deployer.deploy.build_and_deploy")
    async def test_run_concurrent_deployments(self, mock_build_and_deploy, mock_pool):
        mock_pool_instance = mock_pool.return_value.__aenter__.return_value
        mock_pool_instance.apply = mock_build_and_deploy
        mock_build_and_deploy.return_value = DeploymentResult(
            manager=None,
            stack=None,
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
        )
        stack_deployment_requests = [
            StackDeploymentRequest(
                stack_name="stack1",
                iac=b"iac1",
                pulumi_config={},
                deployment_id="deploy_id",
            ),
            StackDeploymentRequest(
                stack_name="stack2",
                iac=b"iac2",
                pulumi_config={},
                deployment_id="deploy_id",
            ),
        ]

        app_order, results = await run_concurrent_deployments(
            "region", "arn", stack_deployment_requests, "user", Path("/tmp")
        )

        mock_pool.assert_called_once()
        mock_pool_instance.apply.assert_has_calls(
            [
                call(
                    mock_build_and_deploy,
                    args=(
                        "region",
                        "arn",
                        "stack1",
                        "user",
                        b"iac1",
                        {},
                        "deploy_id",
                        Path("/tmp") / "stack1",
                    ),
                ),
                call(
                    mock_build_and_deploy,
                    args=(
                        "region",
                        "arn",
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
        assert mock_build_and_deploy.call_count == 2
        assert app_order == ["stack1", "stack2"]
        assert all(isinstance(result, DeploymentResult) for result in results)
        assert all(result.status == DeploymentStatus.SUCCEEDED for result in results)

    @patch("src.deployer.deploy.run_concurrent_deployments")
    async def test_deploy_common_stack(self, mock_run_concurrent_deployments):
        # Arrange
        mock_user_pack = MagicMock(spec=UserPack, id="id")
        mock_common_pack = MagicMock(
            spec=UserApp,
            app_id="id#common",
            version="1",
            get_app_name=MagicMock(return_value="app1"),
            configuration={"key": "value"},
        )
        mock_common_stack = MagicMock(
            spec=CommonStack,
            get_pulumi_configs=MagicMock(return_value={"key": "value"}),
        )
        mock_pulumi_stack = MagicMock(spec=PulumiStack)
        mock_iac_storage = MagicMock(spec=IacStorage, get_iac=Mock(return_value=b"iac"))
        mock_manager = MagicMock()
        mock_run_concurrent_deployments.return_value = (
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
        manager = await deploy_common_stack(
            mock_user_pack,
            mock_common_pack,
            mock_common_stack,
            mock_iac_storage,
            "deploy_id",
            Path("/tmp"),
        )

        # Assert
        mock_iac_storage.get_iac.assert_called_once_with(
            mock_user_pack.id, mock_common_pack.get_app_name(), mock_common_pack.version
        )
        mock_common_stack.get_pulumi_configs.assert_called_once_with(
            mock_common_pack.configuration.items()
        )
        mock_run_concurrent_deployments.assert_called_once_with(
            mock_user_pack.region,
            mock_user_pack.assumed_role_arn,
            [
                StackDeploymentRequest(
                    stack_name=mock_common_pack.app_id,
                    iac=b"iac",
                    pulumi_config=mock_common_stack.get_pulumi_configs.return_value,
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
                UserApp.iac_stack_composite_key.set(
                    mock_pulumi_stack.composite_key.return_value
                ),
            ]
        )
        self.assertEqual(manager, mock_manager)

    @patch("src.deployer.deploy.UserApp")
    async def test_rerun_pack_with_live_state(self, mock_user_app):
        # Arrange
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        mock_app_1 = MagicMock(
            spec=UserApp,
            get_configurations=MagicMock(return_value={"key": "value"}),
            composite_key=MagicMock(return_value="id#app1"),
        )
        mock_app_2 = MagicMock(
            spec=UserApp,
            get_configurations=MagicMock(return_value={"key2": "value2"}),
            composite_key=MagicMock(return_value="id#app2"),
        )
        mock_user_app.get.side_effect = [mock_app_1, mock_app_2]
        mock_user_pack_instance = MagicMock(
            spec=UserPack, id="id", apps={"app1": 1, "app2": 1}
        )
        mock_common_pack = MagicMock(spec=UserApp)
        mock_common_stack = MagicMock(spec=CommonStack)
        mock_iac_storage = MagicMock(spec=IacStorage)
        mock_live_state = MagicMock(
            spec=LiveState,
            to_constraints=MagicMock(return_value=["constraint1", "constraint2"]),
        )
        mock_sps = {
            "app1": MagicMock(spec=StackPack),
            "app2": MagicMock(spec=StackPack),
        }

        # Act
        await rerun_pack_with_live_state(
            mock_user_pack_instance,
            mock_common_pack,
            mock_common_stack,
            mock_iac_storage,
            mock_live_state,
            mock_sps,
            "/tmp",
        )

        # Assert
        mock_user_app.get.assert_has_calls([call("id#app1", 1), call("id#app2", 1)])
        mock_app_1.get_configurations.assert_called_once()
        mock_app_2.get_configurations.assert_called_once()
        mock_user_pack_instance.run_pack.assert_called_once_with(
            mock_sps,
            {"app1": {"key": "value"}, "app2": {"key2": "value2"}},
            "/tmp",
            mock_iac_storage,
            increment_versions=False,
            imports=["constraint1", "constraint2"],
        )

    @patch("src.deployer.deploy.run_concurrent_deployments")
    @patch("src.deployer.deploy.UserApp")
    async def test_deploy_applications(
        self, mock_user_app, mock_run_concurrent_deployments
    ):
        # Arrange
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        mock_app_1 = MagicMock(
            spec=UserApp,
            app_id="id#app1",
            get_app_name=MagicMock(return_value="app1"),
            get_configurations=MagicMock(return_value={"key": "value"}),
            composite_key=MagicMock(return_value="id#app1"),
        )
        mock_app_2 = MagicMock(
            spec=UserApp,
            app_id="id#app2",
            get_app_name=MagicMock(return_value="app2"),
            get_configurations=MagicMock(return_value={"key2": "value2"}),
            composite_key=MagicMock(return_value="id#app2"),
        )
        mock_user_app.get.side_effect = [mock_app_1, mock_app_2]
        mock_user_pack = MagicMock(spec=UserPack, id="id", apps={"app1": 1, "app2": 1})
        mock_iac_storage = MagicMock(
            spec=IacStorage, get_iac=Mock(side_effect=[b"iac1", b"iac2"])
        )
        sp1 = MagicMock(
            spec=StackPack, get_pulumi_configs=MagicMock(return_value={"key": "value"})
        )
        sp2 = MagicMock(
            spec=StackPack,
            get_pulumi_configs=MagicMock(return_value={"key2": "value2"}),
        )
        mock_sps = {"app1": sp1, "app2": sp2}
        mock_run_concurrent_deployments.side_effect = [
            (
                ["id#app1", "id#app2"],
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
        await deploy_applications(
            mock_user_pack, mock_iac_storage, mock_sps, "deploy_id", Path("/tmp")
        )

        # Assert
        mock_user_app.get.assert_has_calls([call("id#app1", 1), call("id#app2", 1)])
        mock_iac_storage.get_iac.assert_has_calls(
            [call("id", "app1", 1), call("id", "app2", 1)]
        )
        mock_app_1.get_configurations.assert_called_once()
        mock_app_2.get_configurations.assert_called_once()
        sp1.get_pulumi_configs.assert_called_once_with({"key": "value"})
        sp2.get_pulumi_configs.assert_called_once_with({"key2": "value2"})
        mock_run_concurrent_deployments.assert_called_once_with(
            mock_user_pack.region,
            mock_user_pack.assumed_role_arn,
            [
                StackDeploymentRequest(
                    stack_name="id#app1",
                    iac=b"iac1",
                    pulumi_config={"key": "value"},
                    deployment_id="deploy_id",
                ),
                StackDeploymentRequest(
                    stack_name="id#app2",
                    iac=b"iac2",
                    pulumi_config={"key2": "value2"},
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
                    mock_run_concurrent_deployments.return_value[1][
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
                    mock_run_concurrent_deployments.return_value[1][
                        0
                    ].stack.composite_key.return_value
                ),
            ]
        )

    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.rerun_pack_with_live_state")
    @patch("src.deployer.deploy.deploy_common_stack")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch("src.deployer.deploy.UserPack")
    @patch("src.deployer.deploy.UserApp")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    async def test_deploy_pack(
        self,
        mock_temp_dir,
        mock_common_stack,
        mock_user_app,
        mock_user_pack,
        mock_get_iac_storage,
        mock_deploy_common_stack,
        mock_rerun_pack_with_live_state,
        mock_deploy_applications,
    ):
        mock_user_pack.COMMON_APP_NAME = UserPack.COMMON_APP_NAME
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        # Arrange
        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_iac_storage = mock_get_iac_storage.return_value
        user_pack = MagicMock(spec=UserPack, id="id", apps={"common": 1})
        mock_user_pack.get.return_value = user_pack
        mock_common_pack = MagicMock(spec=UserApp)
        mock_user_app.get.return_value = mock_common_pack
        common_stack = MagicMock(spec=CommonStack)
        live_state = MagicMock(spec=LiveState)
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )
        mock_common_stack.return_value = common_stack
        mock_deploy_common_stack.return_value = manager
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"

        # Act
        await deploy_pack(pack_id="id", sps=mock_sps, deployment_id="deploy_id")

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack.get.assert_called_once_with("id")
        mock_user_app.get.assert_called_once_with("id#common", 1)
        mock_common_stack.assert_called_once_with([sp1])
        mock_deploy_common_stack.assert_called_once_with(
            user_pack,
            mock_common_pack,
            common_stack,
            mock_iac_storage,
            "deploy_id",
            Path("/tmp"),
        )
        mock_rerun_pack_with_live_state.assert_called_once_with(
            user_pack,
            mock_common_pack,
            common_stack,
            mock_iac_storage,
            live_state,
            mock_sps,
            "/tmp",
        )
        mock_deploy_applications.assert_called_once_with(
            user_pack, mock_iac_storage, mock_sps, "deploy_id", Path("/tmp")
        )
