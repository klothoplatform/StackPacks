from pathlib import Path
from unittest.mock import ANY, MagicMock, call, patch

import aiounittest

from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.engine_service.engine_commands.export_iac import ExportIacRequest
from src.engine_service.engine_commands.run import RunEngineRequest
from src.project import StackPack
from src.project.models.app_deployment import AppDeployment, AppLifecycleStatus
from src.project.storage.iac_storage import IacStorage
from tests.test_utils.pynamo_test import PynamoTest


class TestAppDeployment(PynamoTest, aiounittest.AsyncTestCase):
    models = [AppDeployment]

    def test_to_view_model(self):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
        )
        app.save()

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
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
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
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
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
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
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
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
        )
        app.save()
        new_config = {"new_config": "new_value"}

        # Act
        app.update_configurations(new_config)

        # Assert
        self.assertEqual({"new_config": "new_value"}, app.configuration)

    # Continue with other tests for run_app, get_latest_version, get_latest_deployed_version, composite_key

    @patch("src.project.models.app_deployment.run_engine")
    @patch("src.project.models.app_deployment.export_iac")
    @patch("src.project.models.app_deployment.zip_directory_recurse")
    async def test_run_app(self, mock_zip, mock_export_iac, mock_run_engine):
        # Arrange
        app = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
        )
        mock_stack_pack = MagicMock(
            spec=StackPack, to_constraints=MagicMock(return_value=["constraint1"])
        )
        mock_iac_storage = MagicMock(spec=IacStorage)
        mock_binary_storage = MagicMock(spec=BinaryStorage)
        mock_run_engine.return_value = MagicMock(
            resources_yaml="resources_yaml",
            policy='{"Version": "2012-10-17","Statement": []}',
        )
        imports = ["constraint2"]
        mock_zip.return_value = b"zip_content"
        # Act
        policy = await app.run_app(
            mock_stack_pack, "dir", mock_iac_storage, mock_binary_storage, imports
        )

        # Assert
        mock_stack_pack.to_constraints.assert_called_once_with({"config": "value"})
        mock_run_engine.assert_called_once_with(
            RunEngineRequest(constraints=["constraint1", "constraint2"], tmp_dir="dir")
        )
        mock_export_iac.assert_called_once_with(
            ExportIacRequest(
                input_graph="resources_yaml", name="project_id", tmp_dir="dir"
            )
        )
        mock_stack_pack.copy_files.assert_called_once_with(
            {"config": "value"}, Path("dir")
        )
        mock_zip.assert_called_once_with(ANY, "dir")
        mock_iac_storage.write_iac.assert_called_once_with(
            "project_id", "app", 1, b"zip_content"
        )
        mock_binary_storage.ensure_binary.assert_has_calls(
            [
                call(Binary.ENGINE),
                call(Binary.IAC),
            ]
        )
        self.assertEqual(
            policy.__str__(), '{\n    "Version": "2012-10-17",\n    "Statement": []\n}'
        )

    def test_get_latest_version(self):
        # Arrange
        appv1 = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
        )
        appv1.save()
        appv2 = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 2),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
        )
        appv2.save()
        appv2 = AppDeployment.get(
            "project_id", AppDeployment.compose_range_key("app", 2)
        )

        # Act
        latest_version = AppDeployment.get_latest_version("project_id", "app")

        # Assert
        self.assertEqual(appv2, latest_version)

    def test_get_latest_deployed_version(self):
        # Arrange
        appv1 = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 1),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
            deployments=["deployment1"],
        )
        appv1.save()
        appv2 = AppDeployment(
            project_id="project_id",
            range_key=AppDeployment.compose_range_key("app", 2),
            created_by="created_by",
            configuration={"config": "value"},
            display_name="My App",
            status=AppLifecycleStatus.NEW.value,
            status_reason="status_reason",
        )
        appv2.save()

        # Act
        latest_version = AppDeployment.get_latest_deployed_version("project_id", "app")

        # Assert
        appv1.refresh()
        self.assertEqual(appv1, latest_version)

    def test_compose_range_key(self):
        # Act
        composite_key = AppDeployment.compose_range_key("app_id", 1)

        # Assert
        self.assertEqual(f"app_id#{1:08}", composite_key)
