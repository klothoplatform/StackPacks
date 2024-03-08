import os

import boto3

from src.stack_pack.storage.iac_storage import IacStorage

if os.getenv("IAC_BUCKET", None) is None:
    s3_resource = boto3.resource(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="minio",
        aws_secret_access_key="minio123",
    )
else:
    s3_resource = boto3.resource("s3")


ses_client = boto3.client("sesv2", endpoint_url=os.environ.get("SES_ENDPOINT", None))


def create_iac_bucket():
    return s3_resource.Bucket(os.environ.get("IAC_BUCKET", "iac-store"))


def get_iac_storage():
    return IacStorage(create_iac_bucket())
