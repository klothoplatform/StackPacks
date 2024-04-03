from unittest.mock import ANY, AsyncMock, MagicMock, call, patch, PropertyMock

import aiounittest
from pynamodb.exceptions import DoesNotExist

from src.engine_service.binaries.fetcher import BinaryStorage
from src.project import ConfigValues, Resources, StackPack, StackParts
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import (
    AppLifecycleStatus,
    AppDeploymentView,
    AppDeployment,
)
from src.project.models.project import Project
from src.project.storage.iac_storage import IacStorage
from src.util.aws.iam import Policy
from src.util.tmp import TempDir
from tests.test_utils.pynamo_test import PynamoTest


class TestProject(PynamoTest, aiounittest.AsyncTestCase):
    models = [Project, AppDeployment]

    def setUp(self) -> None:
        super().setUp()

        self.project = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"common": 1, "app1": 1, "app2": 2},
            region="region",
            assumed_role_arn="arn",
            features=["feature1"],
        )
        self.project.save()

        self.mock_stack_packs = {
            "app1": MagicMock(
                spec=StackPack.__fields__.keys(),
                base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
            ),
            "app2": MagicMock(
                spec=StackPack.__fields__.keys(),
                base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
            ),
        }
        for key, mock in self.mock_stack_packs.items():
            mock.return_value.name = PropertyMock(return_value=key)
        self.config: dict[str, ConfigValues] = {
            "app1": ConfigValues(),
            "app2": ConfigValues(),
            "common": ConfigValues(),
        }
        self.mock_iac_storage = MagicMock(spec=IacStorage)
        self.mock_binary_storage = MagicMock(spec=BinaryStorage)
        self.temp_dir = TempDir()
        return super().setUp()

    def tearDown(self) -> None:
        for key, mock in self.mock_stack_packs.items():
            mock.reset_mock()
        for key in self.config.keys():
            self.config[key] = ConfigValues()
        self.mock_iac_storage.reset_mock()
        self.mock_binary_storage.reset_mock()
        self.temp_dir.cleanup()
        return super().tearDown()

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_base(self, mock_common_stack, mock_run_app):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        expected_policy = Policy('{"Version": "2012-10-17","Statement": []}')
        mock_run_app.return_value = expected_policy
        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="created_by",
            configuration=dict(self.config.get("common")),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        common_app.save()

        # Act
        policy = await self.project.run_base(
            self.mock_stack_packs,
            dict(self.config.get("common")),
            self.mock_iac_storage,
            self.mock_binary_storage,
            f"{self.temp_dir.dir}",
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        common_app.run_app.assert_called_once_with(
            common_stack,
            f"{self.temp_dir.dir}/common",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )

        self.assertEqual({"common": 2, "app1": 1, "app2": 2}, self.project.apps)
        self.assertEqual(str(expected_policy), str(policy))
        self.assertEqual({"id"}, common_app.deployments)

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_base_latest_not_deployed(self, mock_common_stack, mock_run_app):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        expected_policy = Policy('{"Version": "2012-10-17","Statement": []}')
        mock_run_app.return_value = expected_policy
        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="created_by",
            configuration=dict(self.config.get("common")),
            status=AppLifecycleStatus.NEW.value,
            deployments=None,
        )
        common_app.save()

        # Act
        policy = await self.project.run_base(
            self.mock_stack_packs,
            dict(self.config.get("common")),
            self.mock_iac_storage,
            self.mock_binary_storage,
            f"{self.temp_dir.dir}",
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        self.assertEqual({"common": 1, "app1": 1, "app2": 2}, self.project.apps)
        self.assertEqual(str(expected_policy), str(policy))

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_base_does_not_exist(self, mock_common_stack, mock_run_app):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        expected_policy = Policy('{"Version": "2012-10-17","Statement": []}')
        mock_run_app.return_value = expected_policy
        self.assertRaises(DoesNotExist, lambda: AppDeployment.get("id", AppDeployment.compose_range_key("common", 1)))

        # Act
        policy = await self.project.run_base(
            self.mock_stack_packs,
            dict(self.config.get("common")),
            self.mock_iac_storage,
            self.mock_binary_storage,
            f"{self.temp_dir.dir}",
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        self.assertEqual({"common": 1, "app1": 1, "app2": 2}, self.project.apps)
        self.assertEqual(str(expected_policy), str(policy))
        self.assertIsNotNone(AppDeployment.get("id", AppDeployment.compose_range_key("common", 1)))

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack", autospec=True)
    async def test_run_pack(self, mock_common_stack, run_app):
        # Arrange
        policy1 = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)

        run_app.side_effect = [policy1, policy2]

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="created_by",
            configuration=self.config.get("app1"),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        app2.save()

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack

        # Act
        policy = await self.project.run_pack(
            self.mock_stack_packs,
            self.config,
            f"{self.temp_dir.dir}",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )

        # Assert

        policy1.combine.assert_called_once_with(policy2)
        self.assertEqual(
            self.project.apps, {"app1": 2, "app2": 3, Project.COMMON_APP_NAME: 1},
        )
        self.assertEqual(policy1, policy)
        self.assertEqual({"id"}, app1.deployments)
        self.assertEqual({"id"}, app2.deployments)

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_pack_favors_imports(self, mock_common_stack, mock_run_app):
        # Arrange
        policy1 = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="created_by",
            configuration=self.config.get("app1"),
            status=AppLifecycleStatus.NEW.value,
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            status=AppLifecycleStatus.NEW.value,
        )
        app2.save()

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack
        mock_run_app.side_effect = [policy1, policy2]

        imports = [
            {
                "scope": "application",
                "operator": "import",
                "node": "test",
            }
        ]
        # Act
        policy = await self.project.run_pack(
            self.mock_stack_packs,
            self.config,
            f"{self.temp_dir.dir}",
            self.mock_iac_storage,
            self.mock_binary_storage,
            imports=imports,
        )

        # Assert
        policy1.combine.assert_called_once_with(policy2)
        self.assertEqual(
            {"app1": 1, "app2": 2, Project.COMMON_APP_NAME: 1}, self.project.apps
        )
        self.assertEqual(policy1, policy)

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_pack_app_doesnt_exist(self, mock_common_stack, mock_run_app):
        # Arrange
        policy1 = MagicMock(spec=Policy)
        policy2 = MagicMock(spec=Policy)

        mock_run_app.side_effect = [policy1, policy2]

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        app2.save()

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack

        # Act
        policy = await self.project.run_pack(
            self.mock_stack_packs,
            self.config,
            f"{self.temp_dir.dir}",
            self.mock_iac_storage,
            self.mock_binary_storage,
        )

        # Assert
        policy1.combine.assert_called_once_with(policy2)
        self.assertEqual(
            {"app1": 1, "app2": 3, Project.COMMON_APP_NAME: 1}, self.project.apps,
        )
        self.assertEqual(policy1, policy)

    async def test_run_pack_invalid_stack_name(self):
        # Arrange
        project = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )
        mock_stack_packs = {
            "app1": MagicMock(spec=StackPack.__fields__.keys()),
        }
        config: dict[str, ConfigValues] = {
            "app1": ConfigValues(),
            "app2": ConfigValues(),
        }
        mock_iac_storage = MagicMock(spec=IacStorage)
        mock_binary_storage = MagicMock(spec=BinaryStorage)
        # Act & Assert
        with self.assertRaises(ValueError):
            await project.run_pack(
                mock_stack_packs,
                config,
                f"{self.temp_dir.dir}",
                mock_iac_storage,
                mock_binary_storage,
            )

    def test_view_model(self):
        # Arrange
        project = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 2, Project.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="created_by",
            configuration=dict(self.config.get("common")),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        common_app.save()

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="created_by",
            configuration=self.config.get("app1"),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        app2.save()

        # Act
        project_view = project.to_view_model()

        # Assert
        self.assertEqual("id", project_view.id)
        self.assertEqual("owner", project_view.owner)
        self.assertEqual("region", project_view.region)
        self.assertEqual("arn", project_view.assumed_role_arn)
        self.assertEqual("created_by", project_view.created_by)
        self.assertEqual(3, len(project_view.stack_packs))
        self.assertIsNotNone(project_view.created_at)

    def test_to_user_stack_does_not_exist(self):
        # Arrange
        project = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 1, Project.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )

        # Act & Assert
        with self.assertRaises(DoesNotExist):
            project.to_view_model()
