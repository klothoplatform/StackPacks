from typing import Optional
import logging
from botocore.exceptions import ClientError
from src.engine_service.engine_commands.run import RunEngineResult
import jsons
import logging
from typing import Optional

from botocore.exceptions import ClientError
from src.util.aws.s3 import put_object, get_object, delete_objects
from src.util.logging import logger


class WriteIacError(Exception):
    pass


class IaCDoesNotExistError(Exception):
    pass


class IacStorage:
    def __init__(self, bucket):
        self._bucket = bucket

    def get_iac(self, id: str) -> Optional[bytes]:
        try:
            obj = self._bucket.Object(IacStorage.get_path_for_iac(id))
            iac_raw = get_object(obj)
            if iac_raw is None:
                raise IaCDoesNotExistError(f"No iac exists for user: {id}")
            if isinstance(iac_raw, str):
                iac_raw = iac_raw.encode()
            return iac_raw
        except FileNotFoundError:
            raise IaCDoesNotExistError(f"No iac exists for user: {id}")
        except ClientError as err:
            # This is only necessary because Klotho's fs implementation
            # doesn't convert this to FileNotFoundError
            if err.response["Error"]["Code"] == "NoSuchKey":
                raise IaCDoesNotExistError(f"No iac exists for user: {id}")
            raise

    def write_iac(self, id: str, content: bytes) -> str:
        key = IacStorage.get_path_for_iac(id)
        try:
            if not isinstance(content, bytes):
                raise TypeError(f"content must be of type bytes, not {type(content)}")
            obj = self._bucket.Object(key)
            put_object(obj, content)
            return key
        except Exception as e:
            raise WriteIacError(
                f"Failed to write iac to S3 bucket {self._bucket.name} and key {key}: {e}"
            )

    def delete_iac(self, id: str):
        keys = [IacStorage.get_path_for_iac(id)]
        try:
            delete_objects(self._bucket, keys)
        except Exception as e:
            raise WriteIacError(
                f"Failed to delete iac from S3 bucket {self._bucket.name} and key {keys}: {e}"
            )

    @staticmethod
    def get_path_for_iac(id: str) -> str:
        return "/".join([id, "iac", "iac.zip"])
