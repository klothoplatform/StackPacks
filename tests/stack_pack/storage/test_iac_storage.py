import aiounittest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from src.stack_pack.models.project import Project
from src.stack_pack.storage.iac_storage import (
    IacStorage,
    WriteIacError,
    IaCDoesNotExistError,
)


class TestIacStorage(aiounittest.AsyncTestCase):
    def setUp(self):
        self.bucket = MagicMock()
        self.iac_storage = IacStorage(self.bucket)
        self.test_id = "test_user"
        self.test_app_name = "test_app"
        self.test_version = 1

    def tearDown(self) -> None:
        self.bucket.reset_mock()
        super().tearDown()

    @patch("src.stack_pack.storage.iac_storage.get_object")
    def test_get_iac(self, mock_get_object):
        mock_get_object.return_value = b"test_content"
        result = self.iac_storage.get_iac(
            self.test_id, self.test_app_name, self.test_version
        )
        self.assertEqual(result, b"test_content")
        self.bucket.Object.assert_called_once_with("test_user/test_app/iac/1/iac.zip")

    @patch("src.stack_pack.storage.iac_storage.get_object")
    def test_get_iac_no_such_key(self, mock_get_object):
        mock_get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "get_object"
        )
        with self.assertRaises(IaCDoesNotExistError):
            self.iac_storage.get_iac(
                self.test_id, self.test_app_name, self.test_version
            )

    @patch("src.stack_pack.storage.iac_storage.put_object")
    def test_write_iac(self, mock_put_object):
        result = self.iac_storage.write_iac(
            self.test_id, self.test_app_name, self.test_version, b"test_content"
        )
        self.assertEqual(result, "test_user/test_app/iac/1/iac.zip")
        self.bucket.Object.assert_called_once_with("test_user/test_app/iac/1/iac.zip")

    @patch("src.stack_pack.storage.iac_storage.put_object")
    def test_write_iac_error(self, mock_put_object):
        mock_put_object.side_effect = Exception("test_error")
        with self.assertRaises(WriteIacError):
            self.iac_storage.write_iac(
                self.test_id, self.test_app_name, self.test_version, b"test_content"
            )

    @patch("src.stack_pack.storage.iac_storage.delete_objects")
    def test_delete_iac(self, mock_delete_objects):
        self.iac_storage.delete_iac(self.test_id, self.test_app_name, self.test_version)
        mock_delete_objects.assert_called_once_with(
            self.bucket, ["test_user/test_app/iac/1/iac.zip"]
        )

    @patch("src.stack_pack.storage.iac_storage.delete_objects")
    def test_delete_iac_error(self, mock_delete_objects):
        mock_delete_objects.side_effect = Exception("test_error")
        with self.assertRaises(WriteIacError):
            self.iac_storage.delete_iac(
                self.test_id, self.test_app_name, self.test_version
            )
