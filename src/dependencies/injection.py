from dataclasses import dataclass
import boto3


def create_sts_client():
    return boto3.client("sts")
