from asyncio import AbstractEventLoop
import aiounittest
from unittest.mock import ANY, Mock, call, patch, MagicMock, AsyncMock

import aiounittest
from unittest.mock import AsyncMock, patch
from fastapi import Request
from src.deployer.models.deployment import DeploymentStatus, PulumiStack
from src.deployer.main import (
    DeploymentResult,
    StackDeploymentRequest
)
from src.deployer.destroy import run_destroy, run_concurrent_destroys, tear_down_pack
from src.stack_pack.models.user_pack import UserPack
from src.stack_pack.models.user_app import UserApp

class TestDestroy(aiounittest.AsyncTestCase):
    @patch("src.deployer.destroy.AppDeployer")
    @patch("src.deployer.destroy.AppBuilder")
    @patch("src.deployer.destroy.Deployment")
    @patch("src.deployer.destroy.PulumiStack")
    @patch('src.deployer.destroy.TempDir')
    async def test_run_destroy(
        self,
        mock_temp_dir: MagicMock,
        mock_pulumi_stack,
        mock_deployment,
        mock_app_builder,
        mock_app_deployer,
    ):
        # Setup mock objects
        mock_builder = MagicMock()
        mock_app_builder.return_value = mock_builder
        mock_deployer = MagicMock()
        mock_app_deployer.return_value = mock_deployer
        mock_deployer.destroy_and_remove_stack = AsyncMock(
            return_value=(MagicMock(), "reason")
        )
        mock_temp_dir.dir = "/tmp"

        cfg = {}

        # Call the method
        await run_destroy("region", "arn", "app", "user", b"iac", cfg, mock_temp_dir)

        # Assert calls
        mock_pulumi_stack.assert_called_once_with(
            project_name="StackPack",
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
        mock_app_builder.assert_called_once_with("/tmp")
        mock_builder.prepare_stack.assert_called_once_with(
            b"iac", mock_pulumi_stack.return_value
        )
        mock_builder.configure_aws.assert_called_once_with(
            mock_builder.prepare_stack.return_value, "arn", "region"
        )
        mock_app_deployer.assert_called_once_with(
            mock_builder.prepare_stack.return_value
        )
        mock_deployer.destroy_and_remove_stack.assert_called_once_with()
        mock_pulumi_stack.return_value.update.assert_called_once()
        mock_deployment.return_value.update.assert_called_once()

    @patch('src.deployer.destroy.Pool')
    @patch('src.deployer.destroy.run_destroy')
    @patch('src.deployer.destroy.TempDir')
    async def test_run_concurrent_destroys(self, mock_temp_dir: MagicMock, mock_run_destroy, mock_pool):
        # Arrange
        mock_temp_dir.return_value = MagicMock()
        mock_pool_instance = mock_pool.return_value.__aenter__.return_value
        mock_pool_instance.apply = mock_run_destroy
        mock_run_destroy.return_value = DeploymentResult(manager=None, stack=None, status=DeploymentStatus.SUCCEEDED, reason="Success")
        stack_deployment_requests = [
            StackDeploymentRequest(stack_name='stack1', iac=b'iac1', pulumi_config={}),
            StackDeploymentRequest(stack_name='stack2', iac=b'iac2', pulumi_config={}),
        ]

        # Act
        app_order, results = await run_concurrent_destroys('region', 'arn', stack_deployment_requests, 'user')

        # Assert
        mock_pool.assert_called_once()
        mock_pool_instance.apply.assert_has_calls([
            call(mock_run_destroy, args=('region', 'arn', 'stack1', 'user', b'iac1', {}, mock_temp_dir.return_value)),
            call(mock_run_destroy, args=('region', 'arn', 'stack2', 'user', b'iac2', {}, mock_temp_dir.return_value)),
        ])
        assert mock_temp_dir.call_count == 2
        assert mock_run_destroy.call_count == 2
        assert app_order == ['stack1', 'stack2']
        assert all(isinstance(result, DeploymentResult) for result in results)
        assert all(result.status == DeploymentStatus.SUCCEEDED for result in results)


    @patch('src.deployer.destroy.get_iac_storage')
    @patch('src.deployer.destroy.UserPack')
    @patch('src.deployer.destroy.UserApp')
    @patch('src.deployer.destroy.run_concurrent_destroys')
    async def test_tear_down_pack(self, mock_run_concurrent_destroys, mock_user_app, mock_user_pack, mock_get_iac_storage):
        # Arrange
        mock_user_pack.COMMON_APP_NAME = UserPack.COMMON_APP_NAME
        mock_user_app.composite_key = lambda a, b: f"{a}#{b}"
        mock_user_pack_instance = UserPack(
            id="id",
            owner="owner",
            region="region",
            assumed_role_arn="arn",
            apps={"app1": 1, "app2": 2, UserPack.COMMON_APP_NAME: 1},
            created_by="created_by",
        )
        mock_user_pack.get.return_value = mock_user_pack_instance
        mock_common_pack = MagicMock(spec=UserApp,
            app_id="id#common",
            version=1,
            get_app_name=MagicMock(return_value="common")
        )
        mock_app_pack_1 = MagicMock(spec=UserApp,
            app_id="id#app1",
            version=1,
            get_app_name=MagicMock(return_value="app1")
        )
        mock_app_pack_2 = MagicMock(spec=UserApp,
            app_id="id#app2",
            version=1,
            get_app_name=MagicMock(return_value="app2")
        )
        mock_user_app.get.side_effect = [mock_app_pack_1, mock_app_pack_2, mock_common_pack]
        mock_common_iac = b'common'
        mock_app_iac_1 = b'iac1'
        mock_app_iac_2 = b'iac2'
        mock_iac_storage = mock_get_iac_storage.return_value
        mock_iac_storage.get_iac.side_effect = [mock_app_iac_1, mock_app_iac_2, mock_common_iac]
        mock_run_concurrent_destroys.side_effect = [
            (["app1", "app2"], [
                DeploymentResult(manager=None, stack = None, status=DeploymentStatus.SUCCEEDED, reason="Success"),
                DeploymentResult(manager=None, stack = None, status=DeploymentStatus.FAILED, reason="Failed")
            ]),
            (["common"], [DeploymentResult(manager=None, stack = None, status=DeploymentStatus.SUCCEEDED, reason="Success")])
        ]

        # Act
        await tear_down_pack(pack_id="id")

        # Assert
        mock_get_iac_storage.assert_called_once()
        mock_user_pack.get.assert_called_once_with("id")
        mock_user_app.get.assert_has_calls([call("id#app1", 1), call("id#app2", 2), call("id#common", 1)])
        mock_iac_storage.get_iac.assert_has_calls([call('id', 'app1', 1), call('id', 'app2', 2), call('id', 'common', 1)])
        mock_run_concurrent_destroys.assert_has_calls([
            call('region', 'arn', [
                StackDeploymentRequest(stack_name='id#app1', iac=b'iac1', pulumi_config={}), 
                StackDeploymentRequest(stack_name='id#app2', iac=b'iac2', pulumi_config={})
                ], 'id'),
            call('region', 'arn', [
                StackDeploymentRequest(stack_name='id#common', iac=b'common', pulumi_config={})
                ], 'id')])
        mock_app_pack_1.update.assert_called_once_with(actions=[
            mock_user_app.status.set(DeploymentStatus.FAILED), 
            mock_user_app.status_reason.set("Failed"),
            mock_user_app.iac_stack_composite_key.set(None)
        ])
        mock_app_pack_2.update.assert_called_once_with(actions=[
            mock_user_app.status.set(DeploymentStatus.FAILED), 
            mock_user_app.status_reason.set("Failed"),
            mock_user_app.iac_stack_composite_key.set(None)
        ])
        mock_common_pack.update.assert_called_once_with(actions=[
            mock_user_app.status.set(DeploymentStatus.SUCCEEDED), 
            mock_user_app.status_reason.set("Success"),
            mock_user_app.iac_stack_composite_key.set(None)
        ])