from pathlib import Path
import tempfile
import aiounittest
from unittest.mock import ANY, patch, MagicMock
from src.engine_service.engine_commands.export_iac import ExportIacRequest
from src.engine_service.engine_commands.run import RunEngineRequest, RunEngineResult
from src.stack_pack.models.user_pack import UserPack
from src.deployer.models.deployment import PulumiStack
from src.stack_pack import ConfigValues


class TestUserPack(aiounittest.AsyncTestCase):

    def tearDown(self):
        self.temp_dir.cleanup()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.user_pack = UserPack(
            id="id",
            owner="owner",
            created_by="created_by",
        )
        self.user_pack.configuration = {
            "stack1": {"key1": "value1"},
            "stack2": {"key2": "value2"},
        }
        self.user_pack.iac_stack_composite_key = "hash_key#range_key"

    def test_get_configurations(self):
        result = self.user_pack.get_configurations()

        self.assertEqual(
            result,
            {
                "stack1": ConfigValues({"key1": "value1"}),
                "stack2": ConfigValues({"key2": "value2"}),
            },
        )

    @patch.object(UserPack, "update")
    def test_update_configurations(self, mock_update):
        configuration = {"stack3": {"key3": "value3"}}

        self.user_pack.update_configurations(configuration)

        mock_update.assert_called_once_with(
            actions=[UserPack.configuration.set(configuration)]
        )

    @patch.object(PulumiStack, "get")
    def test_to_user_stack(self, mock_get):
        # Arrange
        mock_get.return_value = MagicMock(
            status="status", status_reason="status_reason"
        )

        # Act
        result = self.user_pack.to_user_stack()

        # Assert
        self.assertEqual(result.id, self.user_pack.id)
        self.assertEqual(result.owner, self.user_pack.owner)
        self.assertEqual(result.region, self.user_pack.region)
        self.assertEqual(result.assumed_role_arn, self.user_pack.assumed_role_arn)
        self.assertEqual(
            result.configuration,
            {
                "stack1": ConfigValues({"key1": "value1"}),
                "stack2": ConfigValues({"key2": "value2"}),
            },
        )
        self.assertEqual(result.status, "status")
        self.assertEqual(result.status_reason, "status_reason")
        self.assertEqual(result.created_by, self.user_pack.created_by)
        self.assertEqual(result.created_at, self.user_pack.created_at)

    @patch("src.stack_pack.models.user_pack.run_engine")
    @patch("src.stack_pack.models.user_pack.export_iac")
    @patch("src.stack_pack.models.user_pack.zip_directory_recurse")
    @patch("src.stack_pack.models.user_pack.TemporaryDirectory")
    async def test_run_pack(
        self,
        mock_temp_dir,
        mock_zip_directory_recurse,
        mock_export_iac,
        mock_run_engine,
    ):
        # Arrange
        engine_result = RunEngineResult(
            resources_yaml="resources_yaml",
            topology_yaml="topology_yaml",
            iac_topology="iac_topology",
            policy="policy",
        )
        stack1 = MagicMock()
        stack1.to_constraints.return_value = ["constraint1"]
        stack2 = MagicMock()
        stack2.to_constraints.return_value = ["constraint2"]
        mock_run_engine.return_value = engine_result
        mock_zip_directory_recurse.return_value = MagicMock()
        stack_packs = {"stack1": stack1, "stack2": stack2}
        iac_storage = MagicMock()
        mock_temp_dir.return_value.__enter__.return_value = self.temp_dir.name

        # Act
        result, iac = await self.user_pack.run_pack(stack_packs, iac_storage)

        # Assert
        stack1.to_constraints.assert_called_once_with(
            self.user_pack.configuration["stack1"]
        )
        stack2.to_constraints.assert_called_once_with(
            self.user_pack.configuration["stack2"]
        )
        stack1.copy_files.assert_called_once_with(
            self.user_pack.configuration["stack1"], Path(self.temp_dir.name)
        )
        stack2.copy_files.assert_called_once_with(
            self.user_pack.configuration["stack2"], Path(self.temp_dir.name)
        )
        mock_run_engine.assert_called_once_with(
            RunEngineRequest(
                constraints=["constraint1", "constraint2"],
            )
        )
        mock_export_iac.assert_called_once_with(
            ExportIacRequest(
                input_graph=engine_result.resources_yaml,
                name="stack",
                tmp_dir=self.temp_dir.name,
            )
        )
        mock_zip_directory_recurse.assert_called_once_with(ANY, self.temp_dir.name)
        iac_storage.write_iac.assert_called_once_with(
            self.user_pack.id, mock_zip_directory_recurse.return_value
        )
        mock_temp_dir.assert_called_once()
