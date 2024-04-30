from unittest.mock import MagicMock, call, patch

import aiounittest

from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.engine_service.engine_commands.run import RunEngineRequest
from src.project import StackPack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from tests.test_utils.pynamo_test import PynamoTest


class TestAppDeployment(PynamoTest, aiounittest.AsyncTestCase):
    models = [AppDeployment]

    @patch.object(AppDeployment, "get_status")
    def test_to_view_model(self, mock_get_status):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        app.save()
        mock_get_status.return_value = (
            app,
            AppLifecycleStatus.NEW.value,
            "status_reason",
        )
        # Act
        app_deployment_view = app.to_view_model()

        # Assert
        self.assertEqual(
            "app",
            app_deployment_view.app_id,
        )
        self.assertEqual(1, app_deployment_view.version)
        self.assertEqual("created_by", app_deployment_view.created_by)
        self.assertEqual({"config": "value"}, app_deployment_view.configuration)
        self.assertEqual(AppLifecycleStatus.NEW.value, app_deployment_view.status)
        self.assertEqual("status_reason", app_deployment_view.status_reason)
        self.assertEqual("My App", app_deployment_view.display_name)
        self.assertIsNotNone(app_deployment_view.created_at)

    def test_app_id(self):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        app.save()

        # Act
        result = app.app_id()

        # Assert
        self.assertEqual("app", app.app_id())

    def test_version(self):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        app.save()

        # Act
        version = app.version()

        # Assert
        self.assertEqual(1, version)

    def test_get_configurations(self):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )

        # Act
        configurations = app.get_configurations()

        # Assert
        self.assertEqual({"config": "value"}, configurations)

    def test_update_configurations(self):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        app.save()
        new_config = {"new_config": "new_value"}

        # Act
        app.update_configurations(new_config)

        # Assert
        self.assertEqual({"new_config": "new_value"}, app.configuration)

    # Continue with other tests for run_app, get_latest_version, get_latest_deployed_version, composite_key

    @patch("src.project.models.app_deployment.run_engine")
    async def test_run_app(self, mock_run_engine):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        mock_stack_pack = MagicMock(
            spec=StackPack,
            to_constraints=MagicMock(return_value=["constraint1"], region="us-east-1"),
        )
        mock_binary_storage = MagicMock(spec=BinaryStorage)
        mock_run_engine.return_value = MagicMock(
            resources_yaml="resources_yaml",
            policy='{"Version": "2012-10-17","Statement": []}',
        )
        imports = ["constraint2"]
        # Act
        result = await app.run_app(
            mock_stack_pack, "dir", mock_binary_storage, "us-east-1", imports
        )

        # Assert
        mock_stack_pack.to_constraints.assert_called_once_with(
            {"config": "value"}, "us-east-1"
        )
        mock_run_engine.assert_called_once_with(
            RunEngineRequest(
                constraints=["constraint1", "constraint2"],
                tmp_dir="dir",
                tag="project_id/app",
            )
        )
        mock_binary_storage.ensure_binary.assert_has_calls(
            [
                call(Binary.ENGINE),
            ]
        )
        self.assertEqual(result.policy, '{"Version": "2012-10-17","Statement": []}')

    def test_get_latest_version(self):
        # Arrange
        appv1 = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        appv1.save()
        appv2 = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 2),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
        )
        appv2.save()
        appv2 = AppDeployment.get(
            "project_id", AppDeployment.compose_range_key("app", 2)
        )

        # Act
        latest_version = AppDeployment.get_latest_version("project_id", "app")

        # Assert
        self.assertEqual(appv2, latest_version)

    def test_compose_range_key(self):
        # Act
        composite_key = AppDeployment.compose_range_key("app_id", 1)

        # Assert
        self.assertEqual(f"app_id#{1:08}", composite_key)
