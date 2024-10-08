from pathlib import Path
from unittest.mock import MagicMock, call, patch

import aiounittest
from pynamodb.exceptions import DoesNotExist

from src.engine_service.binaries.fetcher import BinaryStorage
from src.project import ConfigValues, Resources, StackParts
from src.project.common_stack import CommonStack, Feature
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


def MockStackPack(app_id: str):
    sp = MagicMock(
        id=app_id,
        version="1",
        description=f"{app_id} desc",
        requires=[],
        base=MagicMock(spec=StackParts, resources=MagicMock(spec=Resources)),
        configuration={},
        outputs={},
        to_constraints=MagicMock(),
    )
    # name is also a input parameter to MagicMock init, but it doesn't set the property
    # so do it manually here
    sp.name = app_id
    return sp


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
            features=[Feature.HEALTH_MONITOR.value],
        )
        self.project.save()

        self.mock_stack_packs = {
            "app1": MockStackPack("app1"),
            "app2": MockStackPack("app2"),
        }
        self.mock_stack_packs["app1"].to_constraints.return_value = [
            {"scope": "application", "operator": "add", "node": "aws:A:app1"}
        ]
        self.mock_stack_packs["app2"].to_constraints.return_value = [
            {"scope": "application", "operator": "add", "node": "aws:B:app2"}
        ]
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

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "run_app")
    async def test_run_common_pack(
        self, mock_run_app, mock_get_latest_deployed_version
    ):
        # Arrange
        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(CommonStack.COMMON_APP_NAME, 1),
            created_by="created_by",
            configuration=dict(self.config.get("common")),
            deployments={"id#1"},
        )
        common_app.save()
        self.project.apps[CommonStack.COMMON_APP_NAME] = (
            1  # project already has the app
        )
        mock_get_latest_deployed_version.return_value = common_app

        # Act
        await self.project.run_common_pack(
            stack_packs=[*self.mock_stack_packs.values()],
            config=ConfigValues(self.config.get("common")),
            features=None,
            binary_storage=self.mock_binary_storage,
            tmp_dir=self.temp_dir,
        )

        # Assert
        common_app.run_app.assert_not_called()
        mock_get_latest_deployed_version.assert_called_once_with(
            "id", CommonStack.COMMON_APP_NAME
        )

        self.assertEqual({"common": 2}, self.project.apps)
        self.assertEqual({"id#1"}, common_app.deployments)

    @patch.object(AppDeployment, "update_policy")
    async def test_run_common_pack_latest_not_deployed(self, mock_update_policy):
        # Arrange

        # Act
        await self.project.run_common_pack(
            stack_packs=[*self.mock_stack_packs.values()],
            config=ConfigValues(self.config.get("common")),
            features=None,
            binary_storage=self.mock_binary_storage,
            tmp_dir=self.temp_dir,
        )

        # Assert
        mock_update_policy.assert_called_once_with(
            self.project.common_stackpack(),
            "/tmp/common",
            self.mock_binary_storage,
            "region",
        )
        self.assertEqual({"common": 1}, self.project.apps)

    @patch.object(AppDeployment, "update_policy")
    async def test_run_common_pack_does_not_exist(self, mock_update_policy):
        # Arrange
        with self.assertRaises(DoesNotExist):
            AppDeployment.get("id", AppDeployment.compose_range_key("common", 1))

        # Act
        await self.project.run_common_pack(
            stack_packs=[*self.mock_stack_packs.values()],
            config=ConfigValues(self.config.get("common")),
            features=None,
            binary_storage=self.mock_binary_storage,
            tmp_dir=self.temp_dir,
        )

        # Assert
        self.assertEqual({"common": 1}, self.project.apps)
        self.assertIsNotNone(
            AppDeployment.get("id", AppDeployment.compose_range_key("common", 1))
        )
        mock_update_policy.assert_called_once_with(
            self.project.common_stackpack(),
            "/tmp/common",
            self.mock_binary_storage,
            "region",
        )

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack", autospec=True)
    async def test_run_pack(
        self, mock_common_stack, run_app, mock_get_latest_deployed_version
    ):
        # Arrange
        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="created_by",
            configuration=self.config.get("app1"),
            deployments={"id"},
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            deployments={"id"},
        )
        app2.save()
        mock_get_latest_deployed_version.side_effect = [app1, app2]

        self.project.apps = {"app1": app1.version(), "app2": app2.version()}

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack
        mock_common_stack.COMMON_APP_NAME = "common"

        # Act
        await self.project.run_packs(
            self.mock_stack_packs,
            self.config,
            self.temp_dir,
            self.mock_binary_storage,
        )

        # Assert

        self.assertEqual(
            {"app1": 2, "app2": 3},
            self.project.apps,
        )
        self.assertEqual({"id"}, app1.deployments)
        self.assertEqual({"id"}, app2.deployments)
        run_app.assert_not_called()
        mock_get_latest_deployed_version.assert_has_calls(
            [call("id", "app1"), call("id", "app2")]
        )

    @patch.object(AppDeployment, "run_app")
    @patch("src.project.models.project.CommonStack")
    async def test_run_pack_favors_imports(self, mock_common_stack, mock_run_app):
        # Arrange
        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="created_by",
            configuration=self.config.get("app1"),
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
        )
        app2.save()

        self.project.apps = {"app1": app1.version(), "app2": app2.version()}

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack
        mock_common_stack.COMMON_APP_NAME = "common"

        imports = [
            {
                "scope": "application",
                "operator": "import",
                "node": "test",
            }
        ]
        # Act
        await self.project.run_packs(
            self.mock_stack_packs,
            self.config,
            self.temp_dir,
            self.mock_binary_storage,
            imports=imports,
        )

        # Assert
        self.assertEqual({"app1": 1, "app2": 2}, self.project.apps)
        mock_run_app.assert_not_called()

    @patch.object(AppDeployment, "get_latest_deployed_version")
    @patch.object(AppDeployment, "update_policy")
    @patch("src.project.models.project.CommonStack")
    async def test_run_pack_app_doesnt_exist(
        self, mock_common_stack, mock_update_policy, mock_get_latest_deployed_version
    ):
        # Arrange
        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            deployments={"id"},
        )
        app2.save()
        self.project.apps = {"app2": app2.version()}

        common_stack = MagicMock(
            spec=CommonStack,
            base=StackParts(resources=Resources({"test": {}})),
        )
        mock_common_stack.return_value = common_stack
        mock_common_stack.COMMON_APP_NAME = "common"
        mock_get_latest_deployed_version.side_effect = [None, app2]

        # Act
        await self.project.run_packs(
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
        mock_update_policy.assert_has_calls(
            [
                call(
                    self.mock_stack_packs["app1"],
                    "/tmp/app1",
                    self.mock_binary_storage,
                    "region",
                    [],
                    dry_run=False,
                ),
                call(
                    self.mock_stack_packs["app2"],
                    "/tmp/app2",
                    self.mock_binary_storage,
                    "region",
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
            apps={"app1": 1, "app2": 1, CommonStack.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )
        mock_stack_packs = {
            "app1": MockStackPack("app1"),
        }
        config: dict[str, ConfigValues] = {
            "app1": ConfigValues(),
            "app2": ConfigValues(),
        }
        mock_binary_storage = MagicMock(spec=BinaryStorage)
        # Act & Assert
        with self.assertRaises(ValueError):
            await project.run_packs(
                mock_stack_packs,
                config,
                self.temp_dir,
                mock_binary_storage,
            )

    @patch.object(AppDeployment, "get_status")
    def test_view_model(self, mock_get_latest_deployed_version):
        # Arrange
        project = Project(
            id="id",
            owner="owner",
            created_by="created_by",
            apps={"app1": 1, "app2": 2, CommonStack.COMMON_APP_NAME: 1},
            region="region",
            assumed_role_arn="arn",
        )

        common_app = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key(CommonStack.COMMON_APP_NAME, 1),
            created_by="created_by",
            configuration=dict(self.config.get("common")),
            deployments={"id#1"},
        )
        common_app.save()

        app1 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app1", 1),
            created_by="created_by",
            configuration=self.config.get("app1"),
            deployments={"id#1"},
        )
        app1.save()

        app2 = AppDeployment(
            project_id="id",
            range_key=AppDeployment.compose_range_key("app2", 2),
            created_by="created_by",
            configuration=self.config.get("app2"),
            deployments={"id#1"},
        )
        app2.save()
        mock_get_latest_deployed_version.return_value = (app1, "INSTALLED", "INSTALLED")

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
