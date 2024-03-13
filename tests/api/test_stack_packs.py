from unittest.mock import AsyncMock, MagicMock, patch

import aiounittest

from src.api.stack_packs import (
    AppRequest,
    StackResponse,
    add_app,
    remove_app,
    update_app,
)
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.models.user_pack import UserPack, UserStack
from src.util.aws.iam import Policy


class TestStackPackRoutes(aiounittest.AsyncTestCase):
    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
    async def test_add_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=UserPack,
            id="user_id",
            apps={"app2": 1, UserPack.COMMON_APP_NAME: 1},
            run_pack=AsyncMock(return_value=policy),
            run_base=AsyncMock(return_value=policy2),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=UserStack)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=UserApp, get_configurations=MagicMock(return_value={"config": "value"})
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
            mock_get_stack_packs.return_value,
            {"app1": {"config1": "value1"}, "app2": {"config": "value"}},
            "/tmp",
        )
        user_pack.run_base.assert_called_once_with(
            list(mock_get_stack_packs.return_value.values()),
            {},
            mock_get_iac_storage.return_value,
            "/tmp",
        )
        policy.combine.assert_called_once_with(policy2)
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
    async def test_add_app_empty_stack(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=UserPack,
            id="user_id",
            apps={},
            run_pack=AsyncMock(return_value=policy),
            run_base=AsyncMock(return_value=policy2),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=UserStack)),
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
            mock_get_stack_packs.return_value, {"app1": {"config1": "value1"}}, "/tmp"
        )
        user_pack.run_base.assert_called_once_with(
            list(mock_get_stack_packs.return_value.values()),
            {},
            mock_get_iac_storage.return_value,
            "/tmp",
        )
        policy.combine.assert_called_once_with(policy2)
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_iac_storage")
    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
    async def test_update_app(
        self,
        mock_get_app,
        mock_get_pack,
        mock_tmp_dir,
        mock_get_user_id,
        mock_get_stack_packs,
        mock_get_iac_storage,
    ):
        # Setup mock objects
        mock_get_user_id.return_value = "user_id"
        mock_get_stack_packs.return_value = {"app1": MagicMock(), "app2": MagicMock()}

        policy = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        user_pack = MagicMock(
            spec=UserPack,
            id="user_id",
            apps={"app1": 1, "app2": 1, UserPack.COMMON_APP_NAME: 1},
            run_pack=AsyncMock(return_value=policy),
            run_base=AsyncMock(return_value=policy2),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=UserStack)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=UserApp, get_configurations=MagicMock(return_value={"config": "value"})
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
            mock_get_stack_packs.return_value,
            {"app1": {"config1": "value1"}, "app2": {"config": "value"}},
            "/tmp",
        )
        user_pack.run_base.assert_called_once_with(
            list(mock_get_stack_packs.return_value.values()),
            {},
            mock_get_iac_storage.return_value,
            "/tmp",
        )
        policy.combine.assert_called_once_with(policy2)
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
    async def test_remove_app(
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
            spec=UserPack,
            id="user_id",
            apps={"app1": 1, "app2": 1},
            run_pack=AsyncMock(return_value=policy),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=UserStack)),
        )
        mock_tmp_dir.return_value.__enter__.return_value = "/tmp"
        user_app = MagicMock(
            spec=UserApp, get_configurations=MagicMock(return_value={"config": "value"})
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
            mock_get_stack_packs.return_value, {"app2": {"config": "value"}}, "/tmp"
        )
        user_pack.save.assert_called_once()

        # Assert response
        self.assertEqual(response.stack, user_pack.to_user_stack.return_value)
        self.assertEqual(response.policy, str(policy))

    @patch("src.api.stack_packs.get_stack_packs")
    @patch("src.api.stack_packs.get_user_id")
    @patch("src.api.stack_packs.TempDir")
    @patch.object(UserPack, "get")
    @patch.object(UserApp, "get")
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
            spec=UserPack,
            id="user_id",
            apps={"app1": 1},
            run_pack=AsyncMock(return_value=policy),
            save=MagicMock(),
            to_user_stack=MagicMock(return_value=MagicMock(spec=UserStack)),
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
