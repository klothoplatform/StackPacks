import asyncclick as click
import boto3
from boto3.dynamodb.conditions import Key
from prettytable import PrettyTable


@click.group()
async def dynamodb():
    pass


@dynamodb.command()
@click.option("--id", prompt="Project ID", help="The ID of the Project.")
async def get_user_pack(id):
    # Create a DynamoDB resource
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")

    # Get the table
    table = dynamodb.Table("Projects")

    # Query the table
    response = table.query(KeyConditionExpression=Key("id").eq(id))

    table = PrettyTable()
    table.field_names = [
        "ID",
        "Owner",
        "Region",
        "Assumed Role ARN",
        "Apps",
        "Created By",
        "Created At",
    ]
    for item in response["Items"]:
        table.add_row(
            [
                item["id"],
                item["owner"],
                item.get("region", None),
                item.get("assumed_role_arn", None),
                item["apps"],
                item["created_by"],
                item["created_at"],
            ]
        )

    print(table)


@dynamodb.command()
@click.option("--start-key", default=None, help="The start key for pagination.")
async def list_user_packs(start_key):
    # Create a DynamoDB resource
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")

    # Get the table
    table = dynamodb.Table("Projects")

    # Scan the table
    if start_key:
        response = table.scan(ExclusiveStartKey=start_key)
    else:
        response = table.scan()

    # Create a pretty table
    table = PrettyTable()
    table.field_names = [
        "ID",
        "Owner",
        "Region",
        "Assumed Role ARN",
        "Apps",
        "Created By",
        "Created At",
    ]

    # Add the items to the table
    for item in response["Items"]:
        table.add_row(
            [
                item["id"],
                item["owner"],
                item.get("region", None),
                item.get("assumed_role_arn", None),
                item["apps"],
                item["created_by"],
                item["created_at"],
            ]
        )

    # Print the table
    print(table)

    # Print the last evaluated key for pagination
    if "LastEvaluatedKey" in response:
        print(f"Last evaluated key: {response['LastEvaluatedKey']}")
    else:
        print("No more items.")


@dynamodb.command()
@click.option("--pack-id", prompt="Pack ID", help="The ID of the pack.")
@click.option("--app-name", prompt="App name", help="The name of the app.")
async def get_user_app(pack_id, app_name):
    # Create a DynamoDB resource
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")

    # Get the table
    table = dynamodb.Table("AppDeployments")

    # Create the app_id
    app_id = f"{pack_id}#{app_name}"

    # Query the table
    response = table.query(KeyConditionExpression=Key("app_id").eq(app_id))

    # Create a pretty table
    table = PrettyTable()
    table.field_names = [
        "App ID",
        "Version",
        "IAC Stack Composite Key",
        "Created By",
        "Created At",
        "Status",
        "Status Reason",
        "Configuration",
    ]

    # Add the items to the table
    for item in response["Items"]:
        table.add_row(
            [
                item["app_id"],
                item["version"],
                item.get("iac_stack_composite_key", None),
                item["created_by"],
                item["created_at"],
                item.get("status", None),
                item.get("status_reason", None),
                item["configuration"],
            ]
        )

    # Print the table
    print(table)
