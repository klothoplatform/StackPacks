from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import aiounittest
from pynamodb.exceptions import DoesNotExist

from src.engine_service.binaries.fetcher import BinaryStorage
from src.project import ConfigValues, Resources, StackPack, StackParts
from src.project.common_stack import CommonStack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


class TestProject(PynamoTest, aiounittest.AsyncTestCase):
    models = [Project, AppDeployment]

    def setUp(self) -> None:
        super().setUp()

        self.project = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={},
            region="region",
            assumed_role_arn="arn",
            features=["feature1"],
        )
        self.project.save()

        self.mock_stack_packs = {
            "app1": MagicMock(
                spec=StackPack.model_fields.keys(),
                base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
                to_constraints=MagicMock(),
            ),
            "app2": MagicMock(
                spec=StackPack.model_fields.keys(),
                base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
                to_constraints=MagicMock(),
            ),
        }
        self.mock_stack_packs["app1"].to_constraints.return_value = [
            {"scope": "application", "operator": "add", "node": "aws:A:app1"}
        ]
        self.mock_stack_packs["app2"].to_constraints.return_value = [
            {"scope": "application", "operator": "add", "node": "aws:B:app2"}
        ]
        for key, mock in self.mock_stack_packs.items():
            mock.return_value.name = PropertyMock(return_value=key)
        self.config: dict[str, ConfigValues] = {
            "app1": ConfigValues(),
            "app2": ConfigValues(),
            "common": ConfigValues(),
        }
        self.mock_binary_storage = MagicMock(spec=BinaryStorage)
        self.temp_dir = Path("/tmp")
        return super().setUp()

    def tearDown(self) -> None:
        for key, mock in self.mock_stack_packs.items():
            mock.reset_mock()
        for key in self.config.keys():
            self.config[key] = ConfigValues()
        self.mock_binary_storage.reset_mock()
        return super().tearDown()

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_base(self, mock_common_stack, mock_run_app):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(Project.COMMON_APP_NAME, 1),
            created_by="created_by",
            configuration=dict(self.config.get("common")),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        common_app.save()
        self.project.apps[Project.COMMON_APP_NAME] = 1  # project already has the app

        # Act
        await self.project.run_base(
            self.mock_stack_packs,
            dict(self.config.get("common")),
            self.mock_binary_storage,
            self.temp_dir,
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        common_app.run_app.assert_not_called()

        self.assertEqual({"common": 1}, self.project.apps)
        self.assertEqual({"id"}, common_app.deployments)

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_base_latest_not_deployed(self, mock_common_stack, mock_run_app):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
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
        await self.project.run_base(
            self.mock_stack_packs,
            dict(self.config.get("common")),
            self.mock_binary_storage,
            self.temp_dir,
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        mock_run_app.assert_called_once_with(
            common_stack, "/tmp/common", self.mock_binary_storage
        )
        self.assertEqual({"common": 1}, self.project.apps)

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_base_does_not_exist(self, mock_common_stack, mock_run_app):
        # Arrange
        common_stack = MagicMock(spec=CommonStack)
        mock_common_stack.return_value = common_stack
        with self.assertRaises(DoesNotExist):
            AppDeployment.get("id", AppDeployment.compose_range_key("common", 1))

        # Act
        await self.project.run_base(
            self.mock_stack_packs,
            dict(self.config.get("common")),
            self.mock_binary_storage,
            self.temp_dir,
        )

        # Assert
        mock_common_stack.assert_called_once_with(self.mock_stack_packs, ["feature1"])
        self.assertEqual({"common": 1}, self.project.apps)
        self.assertIsNotNone(
            AppDeployment.get("id", AppDeployment.compose_range_key("common", 1))
        )
        mock_run_app.assert_called_once_with(
            common_stack, "/tmp/common", self.mock_binary_storage
        )

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack", autospec=True)
    async def test_run_pack(self, mock_common_stack, run_app):
        # Arrange
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

        self.project.apps = {"app1": app1.version(), "app2": app2.version()}

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack

        # Act
        await self.project.run_pack(
            self.mock_stack_packs,
            self.config,
            self.temp_dir,
            self.mock_binary_storage,
        )

        # Assert

        self.assertEqual(
            {"app1": 1, "app2": 2},
            self.project.apps,
        )
        self.assertEqual({"id"}, app1.deployments)
        self.assertEqual({"id"}, app2.deployments)
        run_app.assert_not_called()

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_pack_favors_imports(self, mock_common_stack, mock_run_app):
        # Arrange
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

        self.project.apps = {"app1": app1.version(), "app2": app2.version()}

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
        await self.project.run_pack(
            self.mock_stack_packs,
            self.config,
            self.temp_dir,
            self.mock_binary_storage,
            imports=imports,
        )

        # Assert
        self.assertEqual({"app1": 1, "app2": 2}, self.project.apps)
        mock_run_app.assert_not_called()

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_pack_app_doesnt_exist(self, mock_common_stack, mock_run_app):
        # Arrange
        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            status=AppLifecycleStatus.NEW.value,
            deployments={"id"},
        )
        app2.save()
        self.project.apps = {"app2": app2.version()}

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack

        # Act
        await self.project.run_pack(
            self.mock_stack_packs,
            self.config,
            self.temp_dir,
            self.mock_binary_storage,
        )

        # Assert
        self.assertEqual(
            {"app1": 1, "app2": 2},
            self.project.apps,
        )
        mock_run_app.assert_has_calls(
            [
                call(
                    self.mock_stack_packs["app1"],
                    "/tmp/app1",
                    self.mock_binary_storage,
                    [],
                    dry_run=False,
                ),
                call(
                    self.mock_stack_packs["app2"],
                    "/tmp/app2",
                    self.mock_binary_storage,
                    [],
                    dry_run=False,
                ),
            ]
        )

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
        mock_binary_storage = MagicMock(spec=BinaryStorage)
        # Act & Assert
        with self.assertRaises(ValueError):
            await project.run_pack(
                mock_stack_packs,
                config,
                self.temp_dir,
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
