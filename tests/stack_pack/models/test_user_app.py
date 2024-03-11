from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import aiounittest

from src.deployer.models.deployment import PulumiStack
from src.engine_service.engine_commands.export_iac import ExportIacRequest
from src.engine_service.engine_commands.run import RunEngineRequest
from src.stack_pack import StackPack
from src.stack_pack.models.user_app import UserApp
from src.stack_pack.storage.iac_storage import IacStorage


class TestUserApp(aiounittest.AsyncTestCase):

    @patch.object(PulumiStack, "get")
    @patch.object(UserApp, "get_latest_version_with_status")
    def test_to_user_app(self, mock_get_latest_version_with_status, mock_get):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
            iac_stack_composite_key="iac#stack",
        )
        mock_pulumi_stack = MagicMock(
            spec=PulumiStack, status="status", status_reason="status_reason"
        )
        mock_get.return_value = mock_pulumi_stack
        mock_get_latest_version_with_status.return_value = mock_user_app

        # Act
        app_model = mock_user_app.to_user_app()

        # Assert
        mock_get.assert_called_once()
        mock_get_latest_version_with_status.assert_called_once_with("id#app")
        self.assertEqual(app_model.app_id, "id#app")
        self.assertEqual(app_model.version, 1)
        self.assertEqual(app_model.created_by, "created_by")
        self.assertEqual(app_model.configuration, {"config": "value"})
        self.assertEqual(app_model.status, mock_pulumi_stack.status)
        self.assertEqual(app_model.status_reason, mock_pulumi_stack.status_reason)

    def test_get_app_name(self):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        app_name = mock_user_app.get_app_name()

        # Assert
        self.assertEqual(app_name, "app")

    def test_get_pack_id(self):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        pack_id = mock_user_app.get_pack_id()

        # Assert
        self.assertEqual(pack_id, "id")

    def test_get_configurations(self):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        configurations = mock_user_app.get_configurations()

        # Assert
        self.assertEqual(configurations, {"config": "value"})

    @patch.object(UserApp, "update")
    def test_update_configurations(self, mock_update):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        new_config = {"new_config": "new_value"}

        # Act
        mock_user_app.update_configurations(new_config)

        # Assert
        mock_update.assert_called_once()

    # Continue with other tests for run_app, get_latest_version, get_latest_version_with_status, composite_key

    @patch("src.stack_pack.models.user_app.run_engine")
    @patch("src.stack_pack.models.user_app.export_iac")
    @patch("src.stack_pack.models.user_app.zip_directory_recurse")
    async def test_run_app(self, mock_zip, mock_export_iac, mock_run_engine):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        mock_stack_pack = MagicMock(
            spec=StackPack, to_constraints=MagicMock(return_value=["constraint1"])
        )
        mock_iac_storage = MagicMock(spec=IacStorage)
        mock_run_engine.return_value = MagicMock(
            resources_yaml="resources_yaml",
            policy='{"Version": "2012-10-17","Statement": []}',
        )
        imports = ["constraint2"]
        mock_zip.return_value = b"zip_content"
        # Act
        policy = await mock_user_app.run_app(
            mock_stack_pack, "dir", mock_iac_storage, imports
        )

        # Assert
        mock_stack_pack.to_constraints.assert_called_once_with({"config": "value"})
        mock_run_engine.assert_called_once_with(
            RunEngineRequest(constraints=["constraint1", "constraint2"], tmp_dir="dir")
        )
        mock_export_iac.assert_called_once_with(
            ExportIacRequest(input_graph="resources_yaml", name="id", tmp_dir="dir")
        )
        mock_stack_pack.copy_files.assert_called_once_with(
            {"config": "value"}, Path("dir")
        )
        mock_zip.assert_called_once_with(ANY, "dir")
        mock_iac_storage.write_iac.assert_called_once_with(
            "id", "app", 1, b"zip_content"
        )
        self.assertEqual(
            policy.__str__(), '{\n    "Version": "2012-10-17",\n    "Statement": []\n}'
        )

    @patch.object(UserApp, "query")
    def test_get_latest_version(self, mock_query):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        mock_query.return_value = [MagicMock(spec=UserApp)]

        # Act
        latest_version = UserApp.get_latest_version("id#app")

        # Assert
        mock_query.assert_called_once()
        self.assertEqual(latest_version, mock_query.return_value[0])

    @patch.object(UserApp, "query")
    def test_get_latest_version_with_status(self, mock_query):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        mock_query.return_value = [MagicMock(spec=UserApp)]

        # Act
        latest_version = UserApp.get_latest_version_with_status("id#app")

        # Assert
        mock_query.assert_called_once()
        self.assertEqual(latest_version, mock_query.return_value[0])

    def test_composite_key(self):
        # Arrange
        mock_user_app = UserApp(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        composite_key = UserApp.composite_key("id", "app")

        # Assert
        self.assertEqual(composite_key, "id#app")
        # Assert
        self.assertEqual(composite_key, "id#app")
