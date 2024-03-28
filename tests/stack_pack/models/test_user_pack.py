from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import aiounittest
from pynamodb.exceptions import DoesNotExist

from src.engine_service.binaries.fetcher import BinaryStorage
from src.stack_pack import ConfigValues, Resources, StackPack, StackParts
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.models.app_deployment import (
    AppLifecycleStatus,
    AppModel,
    AppDeployment,
)
from src.stack_pack.models.project import Project
from src.stack_pack.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
from src.util.tmp import TempDir


class TestProject(aiounittest.AsyncTestCase):

    def setUp(self) -> None:
        self.user_pack = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"common": 1, "app1": 1, "app2": 2},
            region="region",
            assumed_role_arn="arn",
            features=["feature1"],
        )
        self.mock_stack_packs = {
            "app1": MagicMock(
                spec=StackPack,
                base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
            ),
            "app2": MagicMock(
                spec=StackPack,
                base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
            ),
        }
        self.config: dict[str, MagicMock] = {
            "app1": MagicMock(spec=ConfigValues),
            "app2": MagicMock(spec=ConfigValues),
            "common": MagicMock(spec=ConfigValues),
        }
        self.mock_iac_storage = MagicMock(spec=IacStorage)
        self.mock_binary_storage = MagicMock(spec=BinaryStorage)
        self.temp_dir = TempDir()
        return super().setUp()

    def tearDown(self) -> None:
        for key, mock in self.mock_stack_packs.items():
            mock.reset_mock()
        for key, mock in self.config.items():
            mock.reset_mock()
        self.mock_iac_storage.reset_mock()
        self.mock_binary_storage.reset_mock()
        self.temp_dir.cleanup()
        return super().tearDown()

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "get")
    @patch("src.stack_pack.models.project.CommonStack")
    async def test_run_base(self, mock_common_stack, mock_get, mock_get_latest):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        common_app = MagicMock(
            spec=AppDeployment,
            version=1,
            get_app_name=MagicMock(return_value="common"),
            run_app=AsyncMock(
                return_value=Policy('{"Version": "2012-10-17","Statement": []}')
            ),
            deployments={"id"},
        )
        mock_get.return_value = common_app
        mock_get_latest.return_value = MagicMock(spec=AppDeployment, version=1)

        # Act
        policy = await self.user_pack.run_base(
            self.mock_stack_packs,
            self.config.get("common"),
            self.mock_iac_storage,
            self.mock_binary_storage,
            f"{self.temp_dir.dir}",
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        mock_get.assert_called_once_with("id#common", 1)
        mock_get_latest.assert_called_once_with(common_app.app_id)
        common_app.run_app.assert_called_once_with(
            common_stack,
            f"{self.temp_dir.dir}/common",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )
        common_app.save.assert_called_once()
        self.assertEqual(self.user_pack.apps, {"common": 2, "app1": 1, "app2": 2})
        self.assertEqual(
            policy.__str__(),
            Policy('{"Version": "2012-10-17","Statement": []}').__str__(),
        )
        self.assertEqual(common_app.deployments, {})

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "get")
    @patch("src.stack_pack.models.project.CommonStack")
    async def test_run_base_latest_not_deployed(
        self, mock_common_stack, mock_get, mock_get_latest
    ):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        common_app = MagicMock(
            spec=AppDeployment,
            version=1,
            get_app_name=MagicMock(return_value="common"),
            run_app=AsyncMock(
                return_value=Policy('{"Version": "2012-10-17","Statement": []}')
            ),
        )
        mock_get.return_value = common_app
        mock_get_latest.return_value = MagicMock(spec=AppDeployment, version=0)

        # Act
        policy = await self.user_pack.run_base(
            self.mock_stack_packs,
            self.config.get("common"),
            self.mock_iac_storage,
            self.mock_binary_storage,
            f"{self.temp_dir.dir}",
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        mock_get.assert_called_once_with("id#common", 1)
        mock_get_latest.assert_called_once_with(common_app.app_id)
        common_app.run_app.assert_called_once_with(
            common_stack,
            f"{self.temp_dir.dir}/common",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )
        common_app.save.assert_called_once()
        self.assertEqual(self.user_pack.apps, {"common": 1, "app1": 1, "app2": 2})
        self.assertEqual(
            policy.__str__(),
            Policy('{"Version": "2012-10-17","Statement": []}').__str__(),
        )

    @patch("src.stack_pack.models.project.CommonStack")
    @patch("src.stack_pack.models.project.UserApp")
    async def test_run_base_does_not_exist(self, mock_user_app, mock_common_stack):
        # Arrange
        mock_user_app.create_hash_key = lambda a, b: f"{a}#{b}"
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        common_app = MagicMock(
            spec=AppDeployment,
            version=1,
            get_app_name=MagicMock(return_value="common"),
            run_app=AsyncMock(
                return_value=Policy('{"Version": "2012-10-17","Statement": []}')
            ),
        )
        mock_user_app.return_value = common_app
        mock_user_app.get.side_effect = DoesNotExist()

        # Act
        policy = await self.user_pack.run_base(
            self.mock_stack_packs,
            self.config.get("common"),
            self.mock_iac_storage,
            self.mock_binary_storage,
            f"{self.temp_dir.dir}",
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        mock_user_app.get.assert_called_once_with("id#common", 1)
        mock_user_app.assert_called_once_with(
            app_id="id#common",
            version=1,
            created_by="created_by",
            created_at=ANY,
            configuration=self.config.get("common"),
            status=AppLifecycleStatus.NEW.value,
        )
        mock_user_app.get_latest_deployed_version.assert_not_called()
        common_app.run_app.assert_called_once_with(
            common_stack,
            f"{self.temp_dir.dir}/common",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )
        common_app.save.assert_called_once()
        self.assertEqual(self.user_pack.apps, {"common": 1, "app1": 1, "app2": 2})
        self.assertEqual(
            policy.__str__(),
            Policy('{"Version": "2012-10-17","Statement": []}').__str__(),
        )

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "get")
    @patch("src.stack_pack.models.project.CommonStack")
    async def test_run_pack(self, mock_common_stack, mock_get, mock_get_latest):
        # Arrange
        policy1 = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        mock_app_1 = MagicMock(
            spec=AppDeployment,
            version=1,
            run_app=AsyncMock(return_value=policy1),
            get_app_name=MagicMock(return_value="app1"),
            deployments={"id"},
        )
        mock_app_2 = MagicMock(
            spec=AppDeployment,
            version=2,
            run_app=AsyncMock(return_value=policy2),
            get_app_name=MagicMock(return_value="app2"),
            deployments={"id"},
        )
        mock_get.side_effect = [mock_app_1, mock_app_2]
        mock_get_latest.side_effect = [
            MagicMock(spec=AppDeployment, version=1),
            MagicMock(spec=AppDeployment, version=1),
        ]
        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack

        # Act
        policy = await self.user_pack.run_pack(
            self.mock_stack_packs,
            self.config,
            f"{self.temp_dir.dir}",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )

        # Assert
        mock_get.assert_has_calls([call("id#app1", 1), call("id#app2", 2)])
        mock_get_latest.assert_has_calls(
            [call(mock_app_1.app_id), call(mock_app_2.app_id)]
        )
        mock_app_1.run_app.assert_called_once_with(
            self.mock_stack_packs.get("app1"),
            f"{self.temp_dir.dir}/app1",
            self.mock_iac_storage,
            self.mock_binary_storage,
            [],
        )
        mock_app_2.run_app.assert_called_once_with(
            self.mock_stack_packs.get("app2"),
            f"{self.temp_dir.dir}/app2",
            self.mock_iac_storage,
            self.mock_binary_storage,
            [],
        )
        mock_app_1.save.assert_called_once()
        mock_app_2.save.assert_called_once()
        policy1.combine.assert_called_once_with(policy2)
        self.assertEqual(
            self.user_pack.apps, {"app1": 2, "app2": 2, Project.COMMON_APP_NAME: 1}
        )
        self.assertEqual(policy, policy1)
        self.assertEqual(mock_app_1.deployments, {})
        self.assertEqual(mock_app_2.deployments, {"id"})

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "get")
    @patch("src.stack_pack.models.project.CommonStack")
    async def test_run_pack_favors_imports(
        self, mock_common_stack, mock_get, mock_get_latest
    ):
        # Arrange
        policy1 = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        mock_app_1 = MagicMock(
            spec=AppDeployment,
            version=1,
            run_app=AsyncMock(return_value=policy1),
            get_app_name=MagicMock(return_value="app1"),
        )
        mock_app_2 = MagicMock(
            spec=AppDeployment,
            version=2,
            run_app=AsyncMock(return_value=policy2),
            get_app_name=MagicMock(return_value="app2"),
        )
        mock_get.side_effect = [mock_app_1, mock_app_2]
        mock_get_latest.side_effect = [
            MagicMock(spec=AppDeployment, version=1),
            MagicMock(spec=AppDeployment, version=1),
        ]
        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack

        imports = [
            {
                "scope": "application",
                "operator": "import",
                "node": "test",
            }
        ]
        # Act
        policy = await self.user_pack.run_pack(
            self.mock_stack_packs,
            self.config,
            f"{self.temp_dir.dir}",
            self.mock_iac_storage,
            self.mock_binary_storage,
            imports=imports,
        )

        # Assert
        mock_get.assert_has_calls([call("id#app1", 1), call("id#app2", 2)])
        mock_get_latest.assert_has_calls(
            [call(mock_app_1.app_id), call(mock_app_2.app_id)]
        )
        mock_app_1.run_app.assert_called_once_with(
            self.mock_stack_packs.get("app1"),
            f"{self.temp_dir.dir}/app1",
            self.mock_iac_storage,
            self.mock_binary_storage,
            imports,
        )
        mock_app_2.run_app.assert_called_once_with(
            self.mock_stack_packs.get("app2"),
            f"{self.temp_dir.dir}/app2",
            self.mock_iac_storage,
            self.mock_binary_storage,
            imports,
        )
        mock_app_1.save.assert_called_once()
        mock_app_2.save.assert_called_once()
        self.mock_stack_packs.get("app1").base.resources.update.assert_not_called()
        self.mock_stack_packs.get("app2").base.resources.update.assert_not_called()
        policy1.combine.assert_called_once_with(policy2)
        self.assertEqual(
            self.user_pack.apps, {"app1": 2, "app2": 2, Project.COMMON_APP_NAME: 1}
        )
        self.assertEqual(policy, policy1)

    @patch("src.stack_pack.models.project.UserApp")
    @patch("src.stack_pack.models.project.CommonStack")
    async def test_run_pack_app_doesnt_exist(self, mock_common_stack, mock_user_app):
        # Arrange
        mock_user_app.create_hash_key = lambda a, b: f"{a}#{b}"
        policy1 = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)
        mock_app_1 = MagicMock(
            spec=AppDeployment,
            version=1,
            run_app=AsyncMock(return_value=policy1),
            get_app_name=MagicMock(return_value="app1"),
        )
        mock_app_2 = MagicMock(
            spec=AppDeployment,
            version=2,
            run_app=AsyncMock(return_value=policy2),
            get_app_name=MagicMock(return_value="app2"),
        )
        mock_user_app.return_value = mock_app_1
        mock_user_app.get.side_effect = [DoesNotExist(), mock_app_2]
        mock_user_app.get_latest_deployed_version.side_effect = [
            MagicMock(spec=AppDeployment, version=1),
            MagicMock(spec=AppDeployment, version=1),
        ]
        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack
        # Act
        policy = await self.user_pack.run_pack(
            self.mock_stack_packs,
            self.config,
            f"{self.temp_dir.dir}",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )

        # Assert
        mock_user_app.get.assert_has_calls([call("id#app1", 1), call("id#app2", 2)])
        mock_user_app.get_latest_deployed_version.assert_has_calls(
            [call(mock_app_2.app_id)]
        )
        mock_user_app.assert_called_once_with(
            app_id="id#app1",
            version=1,
            created_by="created_by",
            created_at=ANY,
            configuration=self.config.get("app1"),
            status=AppLifecycleStatus.NEW.value,
        )

        mock_app_1.run_app.assert_called_once_with(
            self.mock_stack_packs.get("app1"),
            f"{self.temp_dir.dir}/app1",
            self.mock_iac_storage,
            self.mock_binary_storage,
            [],
        )
        mock_app_2.run_app.assert_called_once_with(
            self.mock_stack_packs.get("app2"),
            f"{self.temp_dir.dir}/app2",
            self.mock_iac_storage,
            self.mock_binary_storage,
            [],
        )
        mock_app_1.save.assert_called_once()
        mock_app_2.save.assert_called_once()
        policy1.combine.assert_called_once_with(policy2)
        self.assertEqual(
            self.user_pack.apps, {"app1": 1, "app2": 2, Project.COMMON_APP_NAME: 1}
        )
        self.assertEqual(policy, policy1)

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "get")
    async def test_run_pack_invalid_stack_name(self, mock_get, mock_get_latest):
        # Arrange
        mock_user_pack = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )
        mock_stack_packs = {
            "app1": MagicMock(spec=StackPack),
        }
        config: dict[str, MagicMock] = {
            "app1": MagicMock(spec=ConfigValues),
            "app2": MagicMock(spec=ConfigValues),
        }
        mock_iac_storage = MagicMock(spec=IacStorage)
        mock_binary_storage = MagicMock(spec=BinaryStorage)
        mock_get.return_value = MagicMock(spec=AppDeployment, version=1)
        mock_get_latest.return_value = MagicMock(spec=AppDeployment, version=1)
        # Act & Assert
        with self.assertRaises(ValueError):
            await mock_user_pack.run_pack(
                mock_stack_packs,
                config,
                f"{self.temp_dir.dir}",
                mock_iac_storage,
                mock_binary_storage,
            )

    @patch.object(AppDeployment, "get")
    def test_to_user_stack(self, mock_get):
        # Arrange
        mock_user_pack = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )
        mock_app = MagicMock(
            spec=AppDeployment,
            to_user_app=MagicMock(return_value=MagicMock(spec=AppModel)),
        )
        mock_get.return_value = mock_app

        # Act
        user_stack = mock_user_pack.to_view_model()

        # Assert
        mock_get.assert_has_calls(
            [
                call("id#app1", 1),
                call().to_user_app(),
                call("id#app2", 1),
                call().to_user_app(),
                call("id#common", 1),
                call().to_user_app(),
            ]
        )
        mock_app.to_user_app.assert_has_calls([call(), call(), call()])
        self.assertEqual(user_stack.workflow_id, "id")
        self.assertEqual(user_stack.owner, "owner")
        self.assertEqual(user_stack.region, "region")
        self.assertEqual(user_stack.assumed_role_arn, "arn")
        self.assertEqual(user_stack.created_by, "created_by")
        self.assertEqual(len(user_stack.stack_packs), 3)

    @patch.object(AppDeployment, "get")
    def test_to_user_stack_does_not_exist(self, mock_get):
        # Arrange
        mock_user_pack = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )
        mock_get.side_effect = DoesNotExist()

        # Act & Assert
        with self.assertRaises(DoesNotExist):
            mock_user_pack.to_view_model()
