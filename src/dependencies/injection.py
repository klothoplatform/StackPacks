import os

import boto3

from src.engine_service.binaries.fetcher import BinaryStorage
from src.project.storage.iac_storage import IacStorage

if os.getenv("STACK_SNAP_BINARIES_BUCKET_NAME", None) is None:
    s3_resource = boto3.resource(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="minio",
        aws_secret_access_key="minio123",
    )
else:
    s3_resource = boto3.resource("s3")


def get_ses_client():
    return boto3.client("sesv2", endpoint_url=os.environ.get("SES_ENDPOINT", None))


def create_iac_bucket():
    return s3_resource.Bucket(os.environ.get("IAC_STORE_BUCKET_NAME", "iac-store"))


def get_iac_storage():
    return IacStorage(create_iac_bucket())


def create_binary_bucket():
    return s3_resource.Bucket(
        os.environ.get("STACK_SNAP_BINARIES_BUCKET_NAME", "binary-store")
    )


def get_binary_storage():
    return BinaryStorage(create_binary_bucket())

def get_pulumi_state_bucket_name():
    return os.environ.get("PULUMI_STATE_BUCKET_NAME", None)