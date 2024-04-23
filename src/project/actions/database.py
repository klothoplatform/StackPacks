import json

import boto3

from src.project import BaseRequirements, StackPack
from src.project.live_state import LiveState
from src.project.models.project import Project
from src.util.aws.sts import assume_role
from src.util.logging import logger


def create_database(
    database_name: str, sp: StackPack, project: Project, live_state: LiveState
):
    logger.info(f"Creating database {database_name}")
    db_manager = None
    if BaseRequirements.POSTGRES in sp.requires:
        db_manager = live_state.resources.get("aws:lambda_function:postgres_manager")
    elif BaseRequirements.MYSQL in sp.requires:
        db_manager = live_state.resources.get("aws:lambda_function:mysql_manager")

    if db_manager is None:
        raise ValueError("No DB Manager found")

    db_manager_arn = db_manager.get("Arn")
    if db_manager_arn is None:
        raise ValueError("No DB Manager Arn found")
    sts_client = boto3.client("sts")
    creds, user = assume_role(
        sts_client, project.assumed_role_arn, project.assumed_role_external_id
    )
    lambda_client = boto3.client(
        "lambda",
        region_name=project.region,
        aws_access_key_id=creds.AccessKeyId,
        aws_secret_access_key=creds.SecretAccessKey,
        aws_session_token=creds.SessionToken,
    )
    response = lambda_client.invoke(
        FunctionName=db_manager_arn,
        InvocationType="RequestResponse",
        Payload=bytes(
            f'{{"action": "create_database", "database_name": "{database_name}"}}',
            encoding="utf-8",
        ),
    )
    logger.info(f"Response: {response}")
    if response.get("StatusCode") != 200:
        logger.error(f"Failed to create database: {response}")
        raise ValueError("Failed to create database")

    payload = response.get("Payload")
    logger.info(f"Payload: {payload}")
    if payload is None:
        logger.error(f"Failed to create database: {response}")
        raise ValueError("Failed to create database")

    result = json.loads(payload.read())
    if result.get("StatusCode") != 200:
        logger.error(f"Failed to create database: {result}")
        raise ValueError("Failed to create database")
    logger.info(f"Result: {result}")
    logger.info(f"Database {database_name} created")
    return result.get("ConnectionString")
