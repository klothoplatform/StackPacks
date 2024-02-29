from dataclasses import dataclass
import boto3
import os

from src.stack_pack.storage.iac_storage import IacStorage


def create_sts_client():
    return boto3.client("sts")

def create_iac_bucket():
    resource = boto3.resource("s3")
    return resource.Bucket(os.environ.get("IAC_BUCKET"))

def get_iac_storage():
    return IacStorage(create_iac_bucket())