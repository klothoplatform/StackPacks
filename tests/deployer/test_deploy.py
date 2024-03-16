from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import aiounittest

from src.deployer.deploy import (
    DeploymentResult,
    StackDeploymentRequest,
    build_and_deploy,
    build_and_deploy_application,
    deploy_app,
    deploy_applications,
    deploy_pack,
    deploy_single,
    rerun_pack_with_live_state,
    run_concurrent_deployments,
)
from src.deployer.models.deployment import (
    DeploymentAction,
    DeploymentStatus,
    PulumiStack,
)
from src.deployer.pulumi.manager import AppManager
from src.engine_service.binaries.fetcher import BinaryStorage
from src.stack_pack import StackPack
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.live_state import LiveState
from src.stack_pack.models.user_app import AppLifecycleStatus, UserApp
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

    @patch("src.deployer.deploy.AppDeployer")
    @patch("src.deployer.deploy.Deployment")
    @patch("src.deployer.deploy.PulumiStack")
    @patch("src.deployer.deploy.AppBuilder")
    @patch("src.deployer.deploy.auto.ConfigValue")
    @patch("src.deployer.deploy.DeploymentDir")
    async def test_build_and_deploy_handles_exception(
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
        mock_deployer.deploy = AsyncMock(side_effect=Exception("error"))

        # Call the method
        cfg = {"key": "value"}
        result = await build_and_deploy(
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
        assert result.reason == "Internal error"

    @patch("src.deployer.deploy.get_iac_storage")
    @patch.object(UserApp, "get")
    @patch.object(UserPack, "get")
    @patch("src.deployer.deploy.build_and_deploy")
    async def test_build_and_deploy_application(
        self,
        mock_build_and_deploy,
        mock_user_pack_get,
        mock_user_app_get,
        mock_get_iac_storage,
    ):
        # Arrange
        mock_user_pack = MagicMock(
            spec=UserPack,
            id="id",
            region="region",
            assumed_role_arn="arn",
            apps={"app1": 1},
        )
        mock_user_pack_get.return_value = mock_user_pack
        mock_user_app = MagicMock(
            spec=UserApp,
            app_id="id#app1",
            get_app_name=MagicMock(return_value="app1"),
            version=1,
        )
        mock_user_app_get.return_value = mock_user_app
        mock_iac_storage = MagicMock(
            spec=IacStorage, get_iac=MagicMock(return_value=b"iac")
        )
        mock_get_iac_storage.return_value = mock_iac_storage
        mock_pulumi_stack = MagicMock(
            spec=PulumiStack, composite_key=MagicMock(return_value="key")
        )
        mock_build_and_deploy.return_value = DeploymentResult(
            manager=MagicMock(spec=AppManager),
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
            stack=mock_pulumi_stack,
        )

        # Act
        result = await build_and_deploy_application(
            "id", "app1", "user", {"key": "value"}, "deploy_id", Path("/tmp")
        )

        # Assert
        mock_user_pack_get.assert_called_once_with("id")
        mock_user_app_get.assert_called_once_with("id#app1", 1)
        mock_get_iac_storage.assert_called_once()
        mock_build_and_deploy.assert_called_once_with(
            "region",
            "arn",
            "id",
            "app1",
            "user",
            b"iac",
            {"key": "value"},
            "deploy_id",
            Path("/tmp/app1"),
        )
        self.assertEqual(
            mock_user_app.transition_status.mock_calls,
            [
                call(
                    DeploymentStatus.IN_PROGRESS,
                    DeploymentAction.DEPLOY,
                    "Deployment in progress",
                ),
                call(DeploymentStatus.SUCCEEDED, DeploymentAction.DEPLOY, "Success"),
            ],
        )
        mock_user_app.update.assert_called_once_with(
            actions=[
                UserApp.iac_stack_composite_key.set("key"),
                UserApp.deployments.add({"deploy_id"}),
            ]
        )
        self.assertEqual(
            result,
            DeploymentResult(
                manager=mock_build_and_deploy.return_value.manager,
                status=DeploymentStatus.SUCCEEDED,
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
        mock_build_and_deploy_application.return_value = DeploymentResult(
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

        app_order, results = await run_concurrent_deployments(
            stack_deployment_requests, "user", Path("/tmp")
        )

        mock_pool.assert_called_once()
        mock_pool_instance.apply.assert_has_calls(
            [
                call(
                    mock_build_and_deploy_application,
                    args=("project", "stack1", "user", {}, "deploy_id", Path("/tmp")),
                ),
                call(
                    mock_build_and_deploy_application,
                    args=("project", "stack2", "user", {}, "deploy_id", Path("/tmp")),
                ),
            ]
        )
        assert app_order == ["stack1", "stack2"]
        assert all(isinstance(result, DeploymentResult) for result in results)
        assert all(result.status == DeploymentStatus.SUCCEEDED for result in results)

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
        mock_binary_storage = MagicMock(spec=BinaryStorage)
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
            mock_binary_storage,
            mock_live_state,
            mock_sps,
            "/tmp",
        )

        # Assert
        mock_user_app.get.assert_has_calls([call("id#app1", 1), call("id#app2", 1)])
        mock_app_1.get_configurations.assert_called_once()
        mock_app_2.get_configurations.assert_called_once()
        mock_user_pack_instance.run_pack.assert_called_once_with(
            stack_packs=mock_sps,
            config={"app1": {"key": "value"}, "app2": {"key2": "value2"}},
            tmp_dir="/tmp",
            iac_storage=mock_iac_storage,
            binary_storage=mock_binary_storage,
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
            get_pack_id=MagicMock(return_value="id"),
            get_app_name=MagicMock(return_value="app1"),
            get_configurations=MagicMock(return_value={"key": "value"}),
            composite_key=MagicMock(return_value="id#app1"),
            transition_status=MagicMock(),
        )
        mock_app_2 = MagicMock(
            spec=UserApp,
            app_id="id#app2",
            get_pack_id=MagicMock(return_value="id"),
            get_app_name=MagicMock(return_value="app2"),
            get_configurations=MagicMock(return_value={"key2": "value2"}),
            composite_key=MagicMock(return_value="id#app2"),
            transition_status=MagicMock(),
        )
        mock_user_app.get.side_effect = [mock_app_1, mock_app_2]
        mock_user_pack = MagicMock(spec=UserPack, id="id", apps={"app1": 1, "app2": 1})
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
        result = await deploy_applications(
            mock_user_pack, mock_sps, "deploy_id", Path("/tmp")
        )

        self.assertTrue(result)
        # Assert
        mock_user_app.get.assert_has_calls([call("id#app1", 1), call("id#app2", 1)])
        mock_app_1.get_configurations.assert_called_once()
        mock_app_2.get_configurations.assert_called_once()
        sp1.get_pulumi_configs.assert_called_once_with({"key": "value"})
        sp2.get_pulumi_configs.assert_called_once_with({"key2": "value2"})
        mock_run_concurrent_deployments.assert_called_once_with(
            [
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app1",
                    pulumi_config={"key": "value"},
                    deployment_id="deploy_id",
                ),
                StackDeploymentRequest(
                    project_name="id",
                    stack_name="app2",
                    pulumi_config={"key2": "value2"},
                    deployment_id="deploy_id",
                ),
            ],
            mock_user_pack.id,
            Path("/tmp"),
        )

    @patch("src.deployer.deploy.run_concurrent_deployments")
    async def test_deploy_app(
        self,
        mock_run_concurrent_deployments,
    ):
        pack = MagicMock(spec=UserPack, id="id", apps={"common": 1})
        app = MagicMock(
            spec=UserApp, get_app_name=MagicMock(return_value="app1"), version=1
        )
        sp = MagicMock(
            spec=StackPack, get_pulumi_configs=MagicMock(return_value={"key": "value"})
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

        result = await deploy_app(pack, app, sp, deployment_id, tmp_dir)

        self.assertEqual(result, d_result)

        sp.get_pulumi_configs.assert_called_once_with(app.get_configurations())
        mock_run_concurrent_deployments.assert_called_once_with(
            [
                StackDeploymentRequest(
                    project_name=pack.id,
                    stack_name=app.get_app_name(),
                    pulumi_config=sp.get_pulumi_configs.return_value,
                    deployment_id=deployment_id,
                )
            ],
            pack.id,
            tmp_dir,
        )

    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch("src.deployer.deploy.get_binary_storage")
    @patch.object(UserApp, "get")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_email")
    @patch("src.deployer.deploy.get_stack_packs")
    async def test_deploy_single(
        self,
        mock_get_stack_packs,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_user_app,
        mock_get_binary_storage,
        mock_get_iac_storage,
        mock_deploy_app,
    ):
        pack = MagicMock(spec=UserPack, id="id", apps={"common": 1})
        app = MagicMock(spec=UserApp, get_app_name=MagicMock(return_value="app1"))
        deployment_id = "deployment_id"
        email = "email"

        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_get_stack_packs.return_value = mock_sps
        iac_storage = mock_get_iac_storage.return_value
        binary_storage = mock_get_binary_storage.return_value
        common_stack = mock_common_stack.return_value
        common_app = mock_user_app.return_value
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        live_state = MagicMock(
            spec=LiveState, to_constraints=MagicMock(return_value=["constraint1"])
        )
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )
        mock_deploy_app.return_value = DeploymentResult(
            manager=manager,
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )

        await deploy_single(pack, app, deployment_id, email)

        mock_get_stack_packs.assert_called_once()
        mock_get_iac_storage.assert_called_once()
        mock_common_stack.assert_called_once_with([sp1])
        mock_user_app.assert_called_once_with("id#common", 1)
        mock_temp_dir.return_value.__enter__.assert_called_once()
        self.assertEqual(
            mock_deploy_app.mock_calls,
            [
                call(pack, common_app, common_stack, deployment_id, Path("/tmp")),
                call(pack, app, sp1, deployment_id, Path("/tmp")),
            ],
        )
        manager.read_deployed_state.assert_called_once()
        app.run_app.assert_called_once_with(
            stack_pack=mock_sps.get("app1"),
            dir="/tmp",
            iac_storage=iac_storage,
            binary_storage=binary_storage,
            imports=["constraint1"],
        )
        mock_get_ses_client.assert_called_once()
        mock_send_email.assert_called_once_with(
            mock_get_ses_client.return_value, email, mock_sps.keys()
        )
        app.update.assert_called_once_with(
            actions=[
                UserApp.status.set(AppLifecycleStatus.PENDING.value),
                UserApp.status_reason.set(
                    f"Updating Common Resources, then deploying {app.get_app_name()}."
                ),
            ]
        )

    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch.object(UserApp, "get")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_email")
    @patch("src.deployer.deploy.get_stack_packs")
    async def test_deploy_single_common_stack_fails(
        self,
        mock_get_stack_packs,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_user_app,
        mock_get_iac_storage,
        mock_deploy_app,
    ):
        pack = MagicMock(spec=UserPack, id="id", apps={"common": 1})
        app = MagicMock(spec=UserApp, get_app_name=MagicMock(return_value="app1"))
        deployment_id = "deployment_id"
        email = "email"

        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_get_stack_packs.return_value = mock_sps
        iac_storage = mock_get_iac_storage.return_value
        common_stack = mock_common_stack.return_value
        common_app = mock_user_app.return_value
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        live_state = MagicMock(
            spec=LiveState, to_constraints=MagicMock(return_value=["constraint1"])
        )
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )
        mock_deploy_app.return_value = DeploymentResult(
            manager=None,
            status=DeploymentStatus.FAILED,
            reason="fail",
            stack=MagicMock(spec=PulumiStack),
        )

        await deploy_single(pack, app, deployment_id, email)

        mock_get_stack_packs.assert_called_once()
        mock_get_iac_storage.assert_called_once()
        mock_common_stack.assert_called_once_with([sp1])
        mock_user_app.assert_called_once_with("id#common", 1)
        mock_temp_dir.return_value.__enter__.assert_called_once()
        mock_deploy_app.assert_called_once_with(
            pack, common_app, common_stack, deployment_id, Path("/tmp")
        )
        manager.read_deployed_state.assert_not_called()
        app.run_app.assert_not_called()
        mock_get_ses_client.assert_not_called()
        mock_send_email.assert_not_called()
        app.update.assert_called_once_with(
            actions=[
                UserApp.status.set(AppLifecycleStatus.PENDING.value),
                UserApp.status_reason.set(
                    f"Updating Common Resources, then deploying {app.get_app_name()}."
                ),
            ]
        )
        app.transition_status.assert_called_once_with(
            DeploymentStatus.FAILED, DeploymentAction.DEPLOY, "fail"
        )

    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.rerun_pack_with_live_state")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_binary_storage")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_email")
    async def test_deploy_pack(
        self,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_user_app,
        mock_user_pack,
        mock_get_iac_storage,
        mock_get_binary_storage,
        mock_deploy_app,
        mock_rerun_pack_with_live_state,
        mock_deploy_applications,
    ):
        # Arrange
        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_iac_storage = mock_get_iac_storage.return_value
        mock_binary_storage = mock_get_binary_storage.return_value
        user_pack = MagicMock(
            spec=UserPack,
            id="id",
            apps={"common": 1, "app1": 1},
            tear_down_in_progress=False,
        )
        mock_user_pack.return_value = user_pack
        mock_common_pack = MagicMock(spec=UserApp)
        mock_app1 = MagicMock(spec=UserApp, app_name="app1")
        mock_user_app.side_effect = [mock_common_pack, mock_app1]
        common_stack = MagicMock(spec=CommonStack)
        live_state = MagicMock(
            spec=LiveState, update=MagicMock(), transition_status=MagicMock()
        )
        manager = MagicMock(
            spec=AppManager, read_deployed_state=AsyncMock(return_value=live_state)
        )
        mock_common_stack.return_value = common_stack
        mock_deploy_app.return_value = DeploymentResult(
            manager=manager,
            status=DeploymentStatus.SUCCEEDED,
            reason="Success",
            stack=MagicMock(spec=PulumiStack),
        )
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        mock_get_ses_client.return_value = MagicMock()

        # Act
        await deploy_pack(
            pack_id="id", sps=mock_sps, deployment_id="deploy_id", email="email"
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack.assert_called_once_with("id")
        self.assertEqual(
            mock_user_app.mock_calls, [call("id#common", 1), call("id#app1", 1)]
        )
        mock_common_stack.assert_called_once_with([sp1])
        mock_deploy_app.assert_called_once_with(
            user_pack,
            mock_common_pack,
            common_stack,
            "deploy_id",
            Path("/tmp"),
        )
        mock_rerun_pack_with_live_state.assert_called_once_with(
            user_pack,
            mock_common_pack,
            common_stack,
            mock_iac_storage,
            mock_binary_storage,
            live_state,
            mock_sps,
            "/tmp",
        )
        mock_deploy_applications.assert_called_once_with(
            user_pack, mock_sps, "deploy_id", Path("/tmp")
        )
        mock_send_email.assert_called_once_with(
            mock_get_ses_client.return_value, "email", mock_sps.keys()
        )

    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.rerun_pack_with_live_state")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch("src.deployer.deploy.UserPack")
    @patch("src.deployer.deploy.UserApp")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.send_email")
    async def test_deploy_pack_blocks_if_teardown_ongoing(
        self,
        mock_send_email,
        mock_common_stack,
        mock_user_app,
        mock_user_pack,
        mock_get_iac_storage,
        mock_deploy_app,
        mock_rerun_pack_with_live_state,
        mock_deploy_applications,
    ):
        mock_user_pack.COMMON_APP_NAME = UserPack.COMMON_APP_NAME
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        # Arrange
        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        user_pack = MagicMock(
            spec=UserPack, id="id", apps={"common": 1}, tear_down_in_progress=True
        )
        mock_user_pack.get.return_value = user_pack

        # Act
        with self.assertRaises(ValueError):
            await deploy_pack(
                pack_id="id", sps=mock_sps, deployment_id="deploy_id", email="email"
            )

            # Assert
            mock_get_iac_storage.assert_called_once()
            mock_user_pack.get.assert_called_once_with("id")
            mock_user_app.get.assert_not_called()
            mock_common_stack.assert_called_once_with([sp1])
            mock_deploy_app.assert_not_called()
            mock_rerun_pack_with_live_state.assert_not_called()
            mock_deploy_applications.assert_not_called()
            mock_send_email.assert_not_called()

    @patch("src.deployer.deploy.deploy_applications")
    @patch("src.deployer.deploy.rerun_pack_with_live_state")
    @patch("src.deployer.deploy.deploy_app")
    @patch("src.deployer.deploy.get_iac_storage")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
    @patch("src.deployer.deploy.CommonStack")
    @patch("src.deployer.deploy.TempDir")
    @patch("src.deployer.deploy.get_ses_client")
    @patch("src.deployer.deploy.send_email")
    async def test_deploy_pack_common_stack_failed(
        self,
        mock_send_email,
        mock_get_ses_client,
        mock_temp_dir,
        mock_common_stack,
        mock_user_app,
        mock_user_pack,
        mock_get_iac_storage,
        mock_deploy_app,
        mock_rerun_pack_with_live_state,
        mock_deploy_applications,
    ):
        # Arrange
        sp1 = MagicMock(spec=StackPack)
        mock_sps = {"app1": sp1}
        mock_iac_storage = mock_get_iac_storage.return_value
        user_pack = MagicMock(
            spec=UserPack,
            id="id",
            apps={"common": 1, "app1": 1},
            tear_down_in_progress=False,
        )
        mock_user_pack.return_value = user_pack
        mock_common_pack = MagicMock(spec=UserApp)
        mock_app1 = MagicMock(spec=UserApp, app_name="app1")
        mock_user_app.side_effect = [mock_common_pack, mock_app1, mock_app1]
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        mock_deploy_app.return_value = DeploymentResult(
            manager=None,
            status=DeploymentStatus.FAILED,
            reason="fail",
            stack=MagicMock(spec=PulumiStack),
        )
        mock_temp_dir.return_value = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = "/tmp"
        mock_get_ses_client.return_value = MagicMock()

        # Act
        await deploy_pack(
            pack_id="id", sps=mock_sps, deployment_id="deploy_id", email="email"
        )

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack.assert_called_once_with("id")
        self.assertEqual(
            mock_user_app.mock_calls,
            [call("id#common", 1), call("id#app1", 1), call("id#app1", 1)],
        )
        mock_common_stack.assert_called_once_with([sp1])
        mock_deploy_app.assert_called_once_with(
            user_pack,
            mock_common_pack,
            common_stack,
            "deploy_id",
            Path("/tmp"),
        )
        mock_rerun_pack_with_live_state.assert_not_called()
        mock_deploy_applications.assert_not_called()
        mock_send_email.assert_not_called()
        mock_app1.update.assert_called_once_with(
            actions=[
                UserApp.status.set(AppLifecycleStatus.PENDING.value),
                UserApp.status_reason.set(
                    f"Updating Common Resources, then deploying {mock_app1.app_name}."
                ),
            ]
        )
        mock_app1.transition_status.assert_called_once_with(
            DeploymentStatus.FAILED, DeploymentAction.DEPLOY, "fail"
        )
