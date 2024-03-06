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

    def get_iac(self, pack_id: str, app_name: str, version: int) -> Optional[bytes]:
        logger.info(
            f"Getting iac for pack_id: {pack_id}, app_name: {app_name}, version: {version}"
        )
        try:
            obj = self._bucket.Object(
                IacStorage.get_path_for_iac(pack_id, app_name, version)
            )
            iac_raw = get_object(obj)
            if iac_raw is None:
                raise IaCDoesNotExistError(f"No iac exists for user: {pack_id}")
            if isinstance(iac_raw, str):
                iac_raw = iac_raw.encode()
            return iac_raw
        except FileNotFoundError:
            raise IaCDoesNotExistError(f"No iac exists for user: {pack_id}")
        except ClientError as err:
            # This is only necessary because Klotho's fs implementation
            # doesn't convert this to FileNotFoundError
            if err.response["Error"]["Code"] == "NoSuchKey":
                raise IaCDoesNotExistError(f"No iac exists for user: {pack_id}")
            raise

    def write_iac(
        self, pack_id: str, app_name: str, version: int, content: bytes
    ) -> str:
        logger.info(
            f"Writing iac for pack_id: {pack_id}, app_name: {app_name}, version: {version}"
        )
        key = IacStorage.get_path_for_iac(pack_id, app_name, version)
        try:
            if not isinstance(content, bytes):
                raise TypeError(f"content must be of type bytes, not {type(content)}")
            obj = self._bucket.Object(key)
            put_object(obj, content)
            logger.info("Wrote %s (size: %d)", id, len(content))
            return key
        except Exception as e:
            raise WriteIacError(
                f"Failed to write iac to S3 bucket {self._bucket.name} and key {key}: {e}"
            )

    def delete_iac(self, pack_id: str, app_name: str, version: int):
        logger.info(
            f"Deleting iac for pack_id: {pack_id}, app_name: {app_name}, version: {version}"
        )
        keys = [IacStorage.get_path_for_iac(pack_id, app_name, version)]
        try:
            delete_objects(self._bucket, keys)
        except Exception as e:
            raise WriteIacError(
                f"Failed to delete iac from S3 bucket {self._bucket.name} and key {keys}: {e}"
            )

    @staticmethod
    def get_path_for_iac(pack_id: str, app_name: str, version: int) -> str:
        return "/".join([pack_id, app_name, "iac", str(version), "iac.zip"])
