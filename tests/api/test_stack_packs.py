from unittest.mock import AsyncMock, MagicMock, patch

import aiounittest
from fastapi import HTTPException
from pynamodb.exceptions import DoesNotExist
from sse_starlette import EventSourceResponse

from src.api.stack_packs import (
    AppRequest,
    StackRequest,
    StackResponse,
    add_app,
    create_stack,
    remove_app,
    stream_deployment_logs,
    update_app,
)
from src.stack_pack.models.app_deployment import AppDeployment
from src.stack_pack.models.project import Project, ProjectView
from src.util.aws.iam import Policy


class TestStackPackRoutes(aiounittest.AsyncTestCase):

    @patch("src.api.stack_packs.get_binary_storage")
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.Project")
    @patch("src.api.stack_packs.TempDir")
    async def test_create_stack(
        self,
        mock_tmp_dir,
        mock_user_pack,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        mock_get_user_id.return_value = "user_id"
        user_stack = ProjectView(
            id="id", owner="user_id", created_by="user_id", created_at=0
        )
        mock_pack = MagicMock(
            spec=Project,
            id="user_id",
            to_user_stack=MagicMock(return_value=user_stack),
        )
        mock_user_pack.get.side_effect = DoesNotExist()
        mock_user_pack.return_value = mock_pack
        sps = {"app1": MagicMock(), "app2": MagicMock()}
        mock_get_stack_packs.return_value = sps
        iac_storage = mock_get_iac_storage.return_value
        binary_storage = mock_get_binary_storage.return_value
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        policy1 = MagicMock(spec=Policy, __str__=MagicMock(return_value="policy1"))
        policy2 = MagicMock(spec=Policy, __str__=MagicMock(return_value="policy2"))
        mock_pack.run_base = AsyncMock(return_value=policy1)
        mock_pack.run_pack = AsyncMock(return_value=policy2)

        response: StackResponse = await create_stack(
            MagicMock(), StackRequest(configuration={"app1": {"config1": "value1"}})
        )

        mock_get_user_id.assert_called_once()
        mock_user_pack.get.assert_called_once_with("user_id")
        mock_user_pack.assert_called_once_with(
            id="user_id",
            owner="user_id",
            created_by="user_id",
            apps={"app1": 0},
            region=None,
            features=["health_monitor"],
            assumed_role_arn=None,
        )
        mock_get_stack_packs.assert_called_once()
        self.assertEqual(mock_get_iac_storage.call_count, 2)
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        mock_pack.run_base.assert_called_once_with(
            stack_packs=list(sps.values()),
            config={},
            iac_storage=iac_storage,
            binary_storage=binary_storage,
            tmp_dir="/tmp",
        )
        mock_pack.run_pack.assert_called_once_with(
            stack_packs=sps,
            config={"app1": {"config1": "value1"}},
            iac_storage=iac_storage,
            binary_storage=binary_storage,
            tmp_dir="/tmp",
        )
        mock_pack.save.assert_called_once()
        policy2.combine.assert_called_once_with(policy1)
        self.assertEqual(response.stack, user_stack)
        self.assertEqual(response.policy, "policy2")

    @patch("src.api.stack_packs.get_binary_storage")
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(Project, "get")
    async def test_create_stack_Stack_exists(
        self,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        mock_get_user_id.return_value = "user_id"
        mock_pack = MagicMock(
            spec=Project,
            id="user_id",
        )
        mock_get_pack.return_value = mock_pack
        sps = {"app1": MagicMock(), "app2": MagicMock()}
        mock_get_stack_packs.return_value = sps

        with self.assertRaises(HTTPException) as e:
            await create_stack(
                MagicMock(), StackRequest(configuration={"app1": {"config1": "value1"}})
            )
        self.assertEqual(e.exception.status_code, 400)
        self.assertEqual(
            e.exception.detail,
            "Stack already exists for this user, use PATCH to update",
        )

        mock_get_user_id.assert_called_once()
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_stack_packs.assert_not_called()
        mock_get_iac_storage.assert_not_called()
        mock_get_binary_storage.assert_called_once()
        mock_tmp_dir.assert_not_called()
        mock_tmp_dir.return_value.__enter__.assert_not_called()
        mock_pack.run_base.assert_not_called()
        mock_pack.run_pack.assert_not_called()
        mock_pack.save.assert_not_called()

    @patch("src.api.stack_packs.get_binary_storage")
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get")
    async def test_add_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app2": 1, Project.COMMON_APP_NAME: 1},
            run_pack=AsyncMock(return_value=policy),
            run_base=AsyncMock(return_value=policy2),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=AppDeployment,
            get_configurations=MagicMock(return_value={"config": "value"}),
        )

        mock_get_pack.return_value = user_pack
        mock_get_app.return_value = user_app

        response: StackResponse = await add_app(
            MagicMock(), "app1", AppRequest(configuration={"config1": "value1"})
        )

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.assert_called_once_with("user_id#app2", 1)
        user_app.get_configurations.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        user_pack.run_pack.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={"app1": {"config1": "value1"}, "app2": {"config": "value"}},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        user_pack.run_base.assert_called_once_with(
            stack_packs=list(mock_get_stack_packs.return_value.values()),
            config={},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        policy.combine.assert_called_once_with(policy2)
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_binary_storage")
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get")
    async def test_add_app_empty_stack(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=Project,
            id="user_id",
            apps={},
            run_pack=AsyncMock(return_value=policy),
            run_base=AsyncMock(return_value=policy2),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"

        mock_get_pack.return_value = user_pack

        response: StackResponse = await add_app(
            MagicMock(), "app1", AppRequest(configuration={"config1": "value1"})
        )

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.assert_not_called()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        user_pack.run_pack.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={"app1": {"config1": "value1"}},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        user_pack.run_base.assert_called_once_with(
            stack_packs=list(mock_get_stack_packs.return_value.values()),
            config={},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        policy.combine.assert_called_once_with(policy2)
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_binary_storage")
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get")
    async def test_update_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            run_pack=AsyncMock(return_value=policy),
            run_base=AsyncMock(return_value=policy2),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=AppDeployment,
            get_configurations=MagicMock(return_value={"config": "value"}),
        )

        mock_get_pack.return_value = user_pack
        mock_get_app.return_value = user_app

        response: StackResponse = await update_app(
            MagicMock(), "app1", AppRequest(configuration={"config1": "value1"})
        )

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.assert_called_once_with("user_id#app2", 1)
        user_app.get_configurations.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        user_pack.run_pack.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={"app1": {"config1": "value1"}, "app2": {"config": "value"}},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        user_pack.run_base.assert_called_once_with(
            stack_packs=list(mock_get_stack_packs.return_value.values()),
            config={},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        policy.combine.assert_called_once_with(policy2)
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_binary_storage")
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get")
    async def test_remove_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app1": 1, "app2": 1},
            run_pack=AsyncMock(return_value=policy),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=AppDeployment,
            get_configurations=MagicMock(return_value={"config": "value"}),
        )

        mock_get_pack.return_value = user_pack
        mock_get_app.return_value = user_app

        response: StackResponse = await remove_app(MagicMock(), "app1")

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.assert_called_once_with("user_id#app2", 1)
        user_app.get_configurations.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        user_pack.run_pack.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={"app2": {"config": "value"}},
            iac_storage=mock_get_iac_storage.return_value,
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get")
    async def test_remove_app_last_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app1": 1},
            run_pack=AsyncMock(return_value=policy),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_get_pack.return_value = user_pack

        response: StackResponse = await remove_app(MagicMock(), "app1")

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.assert_not_called()
        mock_tmp_dir.assert_not_called()
        user_pack.run_pack.assert_not_called()
        self.assertEqual(user_pack.apps, {})
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, None)

    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.DeploymentDir")
    async def test_stream_deployment_logs(self, mock_deploy_dir_ctor, mock_get_user_id):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_deploy_dir = MagicMock()
        mock_deploy_dir_ctor.return_value = mock_deploy_dir
        mock_deploy_log = MagicMock()
        mock_deploy_dir.get_log.return_value = mock_deploy_log
        mock_deploy_log.tail.return_value = MagicMock()

        response: EventSourceResponse = await stream_deployment_logs(
            MagicMock(),
            "app_id",
            "deployment_id",
        )

        # Assert calls
        mock_deploy_dir_ctor.assert_called_once_with("user_id", "deployment_id")
        mock_deploy_dir.get_log.assert_called_once_with("app_id")
        mock_deploy_log.tail.assert_called_once()

        # Assert response
        self.assertEqual(response.status_code, 200)
