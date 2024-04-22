from unittest.mock import AsyncMock, MagicMock, call, patch

import aiounittest
from fastapi import HTTPException
from pynamodb.exceptions import DoesNotExist

from src.api.project_router import (
    AppRequest,
    StackRequest,
    StackResponse,
    UpdateStackRequest,
    add_app,
    create_stack,
    remove_app,
    update_app,
    update_stack,
)
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project, ProjectView
from src.util.aws.iam import Policy
from tests.test_utils.pynamo_test import PynamoTest


class TestProjectRoutes(PynamoTest, aiounittest.AsyncTestCase):
    models = [Project, AppDeployment]

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.Project")
    @patch("src.api.project_router.TempDir")
    async def test_create_project(
        self,
        mock_tmp_dir,
        mock_project,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_binary_storage,
    ):
        mock_get_user_id.return_value = "user_id"
        project_view = ProjectView(
            id="id", owner="user_id", created_by="user_id", created_at=0
        )
        mock_project.get.side_effect = DoesNotExist
        mock_project_instance = MagicMock(
            spec=Project,
            id="user_id",
            to_view_model=MagicMock(return_value=project_view),
            stack_packs=MagicMock(return_value=[]),
        )
        mock_project.get.side_effect = DoesNotExist()
        mock_project.return_value = mock_project_instance
        mock_project_instance.get_policy.return_value = "policy"
        sps = {"app1": MagicMock(), "app2": MagicMock()}
        mock_get_stack_packs.return_value = sps
        binary_storage = mock_get_binary_storage.return_value
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"

        response: StackResponse = await create_stack(
            MagicMock(), StackRequest(configuration={"app1": {"config1": "value1"}})
        )

        mock_get_user_id.assert_called_once()
        mock_project.get.assert_called_once_with("user_id")
        mock_project.assert_called_once_with(
            id="user_id",
            owner="user_id",
            created_by="user_id",
            apps={},
            region=None,
            assumed_role_arn=None,
            assumed_role_external_id=None,
            features=["health_monitor"],
        )
        mock_get_stack_packs.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        mock_project_instance.run_common_pack.assert_called_once_with(
            stack_packs=[sps["app1"]],
            config={},
            binary_storage=binary_storage,
            tmp_dir="/tmp",
        )
        mock_project_instance.run_packs.assert_called_once_with(
            stack_packs={"app1": sps["app1"]},
            config={"app1": {"config1": "value1"}},
            binary_storage=binary_storage,
            tmp_dir="/tmp",
        )
        mock_project_instance.get_policy.assert_called_once()
        self.assertEqual(response.stack, project_view)
        self.assertEqual(response.policy, "policy")

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.TempDir")
    @patch.object(Project, "get")
    async def test_create_stack_Stack_exists(
        self,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
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
        mock_get_binary_storage.assert_called_once()
        mock_tmp_dir.assert_not_called()
        mock_tmp_dir.return_value.__enter__.assert_not_called()
        mock_pack.run_common_pack.assert_not_called()
        mock_pack.run_packs.assert_not_called()
        mock_pack.save.assert_not_called()

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.Project")
    @patch("src.api.project_router.TempDir")
    async def test_update_stack(
        self,
        mock_tmp_dir,
        mock_project,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_binary_storage,
    ):
        mock_get_user_id.return_value = "user_id"
        project_view = ProjectView(
            id="id", owner="user_id", created_by="user_id", created_at=0
        )
        mock_project_instance = MagicMock(
            spec=Project,
            id="user_id",
            to_view_model=MagicMock(return_value=project_view),
        )
        mock_project.get.return_value = mock_project_instance

        mock_project_instance.get_policy.return_value = "policy"
        sps = {"app1": MagicMock(), "app2": MagicMock()}
        mock_get_stack_packs.return_value = sps
        binary_storage = mock_get_binary_storage.return_value
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"

        app = AppDeployment(
            project_id=mock_project_instance.id,
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="user_id",
            status="",
            configuration={"config1": "value0"},
        )
        app.save()

        response: StackResponse = await update_stack(
            MagicMock(),
            UpdateStackRequest(configuration={"app1": {"config1": "value1"}}),
        )

        mock_get_user_id.assert_called_once()
        mock_project.get.assert_called_once_with("user_id")

        mock_get_stack_packs.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        mock_project_instance.run_common_pack.assert_called_once_with(
            stack_packs=[sps["app1"]],
            config={},
            binary_storage=binary_storage,
            tmp_dir="/tmp",
        )
        mock_project_instance.run_packs.assert_called_once_with(
            stack_packs=sps,
            config={"app1": {"config1": "value1"}},
            binary_storage=binary_storage,
            tmp_dir="/tmp",
        )
        mock_project_instance.get_policy.assert_called_once()
        self.assertEqual(response.stack, project_view)
        self.assertEqual(response.policy, "policy")

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.TempDir")
    @patch.object(Project, "get")
    async def test_add_app(
        self,
        mock_get_project,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {
            "app1": MagicMock(id="app1"),
            "app2": MagicMock(id="app2"),
        }

        project = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app2": 1, Project.COMMON_APP_NAME: 1},
            save=MagicMock(),
            to_view_model=MagicMock(return_value=MagicMock(spec=ProjectView)),
            stack_packs=MagicMock(
                return_value=[*mock_get_stack_packs.return_value.values()]
            ),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=AppDeployment,
            get_configurations=MagicMock(return_value={"config": "value"}),
            app_id=MagicMock(return_value="app2"),
        )

        mock_get_project.return_value = project
        project.get_app_deployments = MagicMock(return_value=[user_app])

        response: StackResponse = await add_app(
            MagicMock(), "app1", AppRequest(configuration={"config1": "value1"})
        )

        # Assert calls
        mock_get_project.assert_called_once_with("user_id")
        project.get_app_deployments.assert_called_once()
        user_app.get_configurations.assert_called_once()
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        project.run_packs.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={"app1": {"config1": "value1"}, "app2": {"config": "value"}},
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        project.run_common_pack.assert_called_once_with(
            stack_packs=list(mock_get_stack_packs.return_value.values()),
            config={},
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )

        # Assert response
        self.assertEqual(project.to_view_model.return_value, response.stack)

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.TempDir")
    @patch.object(Project, "get")
    async def test_add_app_empty_stack(
        self,
        mock_get_project,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        project = MagicMock(
            spec=Project,
            id="user_id",
            apps={},
            to_view_model=MagicMock(return_value=MagicMock(spec=ProjectView)),
            get_app_deployments=MagicMock(return_value=[]),
            stack_packs=MagicMock(
                return_value=[*mock_get_stack_packs.return_value.values()]
            ),
        )

        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"

        mock_get_project.return_value = project

        response: StackResponse = await add_app(
            MagicMock(), "app1", AppRequest(configuration={"config1": "value1"})
        )

        # Assert calls
        mock_get_project.assert_called_once_with("user_id")
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        project.run_packs.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={"app1": {"config1": "value1"}},
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        project.run_common_pack.assert_called_once_with(
            stack_packs=[mock_get_stack_packs.return_value["app1"]],
            config={},
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )

        # Assert response
        self.assertEqual(response.stack, project.to_view_model.return_value)

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.TempDir")
    @patch.object(Project, "get")
    @patch.object(AppDeployment, "get")
    async def test_update_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        user_pack = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            run_packs=AsyncMock(),
            run_common_pack=AsyncMock(),
            save=MagicMock(),
            to_view_model=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=AppDeployment,
            get_configurations=MagicMock(return_value={"config": "value"}),
        )

        mock_get_pack.return_value = user_pack
        mock_get_app.return_value = user_app

        response: StackResponse = await update_app(
            MagicMock(),
            "app1",
            AppRequest(configuration={"config": "new_value", "config2": "value2"}),
        )

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.has_calls(
            call("user_id", f"app1#{1:08}"),
            call("user_id", f"app2#{1:08}"),
        )
        self.assertEqual(2, user_app.get_configurations.call_count)
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        user_pack.run_packs.assert_called_once_with(
            stack_packs=mock_get_stack_packs.return_value,
            config={
                "app1": {"config": "new_value", "config2": "value2"},
                "app2": {"config": "value"},
            },
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        user_pack.run_common_pack.assert_called_once_with(
            stack_packs=list(mock_get_stack_packs.return_value.values()),
            config={},
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )
        # Assert response
        self.assertEqual(response.stack, user_pack.to_view_model.return_value)

    @patch("src.api.project_router.get_binary_storage")
    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.TempDir")
    @patch.object(Project, "get")
    async def test_remove_app(
        self,
        mock_get_project,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_binary_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        project = MagicMock(
            spec=Project,
            id="user_id",
            apps={"app1": 1, "app2": 1},
            save=MagicMock(),
            to_view_model=MagicMock(return_value=MagicMock(spec=ProjectView)),
            stack_packs=MagicMock(
                return_value=[*mock_get_stack_packs.return_value.values()]
            ),
            get_app_deployments=MagicMock(
                return_value=[
                    MagicMock(
                        spec=AppDeployment,
                        get_configurations=MagicMock(return_value={"config": "value"}),
                        app_id=MagicMock(return_value="app2"),
                    )
                ]
            ),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"

        mock_get_project.return_value = project

        response: StackResponse = await remove_app(MagicMock(), "app1")

        # Assert calls
        mock_get_project.assert_called_once_with("user_id")
        mock_tmp_dir.assert_called_once()
        mock_tmp_dir.return_value.__enter__.assert_called_once()
        project.run_packs.assert_called_once_with(
            stack_packs={"app2": mock_get_stack_packs.return_value["app2"]},
            config={"app2": {"config": "value"}},
            binary_storage=mock_get_binary_storage.return_value,
            tmp_dir="/tmp",
        )

        # Assert response
        self.assertEqual(response.stack, project.to_view_model.return_value)

    @patch("src.api.project_router.get_stack_packs")
    @patch("src.api.project_router.get_user_id")
    @patch("src.api.project_router.TempDir")
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
            run_packs=AsyncMock(return_value=policy),
            save=MagicMock(),
            to_view_model=MagicMock(return_value=MagicMock(spec=ProjectView)),
        )
        mock_get_pack.return_value = user_pack

        response: StackResponse = await remove_app(MagicMock(), "app1")

        # Assert calls
        mock_get_pack.assert_called_once_with("user_id")
        mock_get_app.assert_not_called()
        mock_tmp_dir.assert_not_called()
        user_pack.run_packs.assert_not_called()
        self.assertEqual(user_pack.apps, {})
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_view_model.return_value)
        self.assertEqual(response.policy, None)
