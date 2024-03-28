from pathlib import Path
from unittest.mock import ANY, MagicMock, call, patch

import aiounittest

from src.engine_service.binaries.fetcher import Binary, BinaryStorage
from src.engine_service.engine_commands.export_iac import ExportIacRequest
from src.engine_service.engine_commands.run import RunEngineRequest
from src.stack_pack import StackPack
from src.stack_pack.models.app_deployment import AppDeployment
from src.stack_pack.storage.iac_storage import IacStorage


class TestUserApp(aiounittest.AsyncTestCase):

    @patch.object(AppDeployment, "get_latest_deployed_version")
    def test_to_user_app(self, mock_get_latest_deployed_version):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        mock_latest_deployed_version = MagicMock(
            spec=AppDeployment,
            iac_stack_composite_key="iac#stack",
            status="status",
            status_reason="status_reason",
        )
        mock_get_latest_deployed_version.return_value = mock_latest_deployed_version

        # Act
        app_model = mock_user_app.to_view_model()

        # Assert
        mock_get_latest_deployed_version.assert_called_once_with("id#app")
        self.assertEqual(app_model.owning_app_id, "id#app")
        self.assertEqual(app_model.version, 1)
        self.assertEqual(app_model.created_by, "created_by")
        self.assertEqual(app_model.configuration, {"config": "value"})
        self.assertEqual(app_model.status, "status")
        self.assertEqual(app_model.status_reason, "status_reason")

    def test_get_app_name(self):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        app_name = mock_user_app.get_app_id()

        # Assert
        self.assertEqual(app_name, "app")

    def test_get_pack_id(self):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        pack_id = mock_user_app.get_project_id()

        # Assert
        self.assertEqual(pack_id, "id")

    def test_get_configurations(self):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        configurations = mock_user_app.get_configurations()

        # Assert
        self.assertEqual(configurations, {"config": "value"})

    @patch.object(AppDeployment, "update")
    def test_update_configurations(self, mock_update):
        # Arrange
        mock_user_app = AppDeployment(
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

    # Continue with other tests for run_app, get_latest_version, get_latest_deployed_version, composite_key

    @patch("src.stack_pack.models.app_deployment.run_engine")
    @patch("src.stack_pack.models.app_deployment.export_iac")
    @patch("src.stack_pack.models.app_deployment.zip_directory_recurse")
    async def test_run_app(self, mock_zip, mock_export_iac, mock_run_engine):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
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
        policy = await mock_user_app.run_app(
            mock_stack_pack, "dir", mock_iac_storage, mock_binary_storage, imports
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
        mock_binary_storage.ensure_binary.assert_has_calls(
            [
                call(Binary.ENGINE),
                call(Binary.IAC),
            ]
        )
        self.assertEqual(
            policy.__str__(), '{\n    "Version": "2012-10-17",\n    "Statement": []\n}'
        )

    @patch.object(AppDeployment, "query")
    def test_get_latest_version(self, mock_query):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        mock_query.return_value = [MagicMock(spec=AppDeployment)]

        # Act
        latest_version = AppDeployment.get_latest_version("id#app")

        # Assert
        mock_query.assert_called_once()
        self.assertEqual(latest_version, mock_query.return_value[0])

    @patch.object(AppDeployment, "query")
    def test_get_latest_deployed_version(self, mock_query):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )
        mock_query.return_value = [MagicMock(spec=AppDeployment)]

        # Act
        latest_version = AppDeployment.get_latest_deployed_version("id#app")

        # Assert
        mock_query.assert_called_once()
        self.assertEqual(latest_version, mock_query.return_value[0])

    def test_composite_key(self):
        # Arrange
        mock_user_app = AppDeployment(
            app_id="id#app",
            version=1,
            created_by="created_by",
            configuration={"config": "value"},
        )

        # Act
        composite_key = AppDeployment.composite_key("id", "app")

        # Assert
        self.assertEqual(composite_key, "id#app")
        # Assert
        self.assertEqual(composite_key, "id#app")
