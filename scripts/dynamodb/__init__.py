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
async def list_user_apps():
    # Create a DynamoDB resource
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")

    # Get the table
    table = dynamodb.Table("AppDeployments")

    # Scan the table
    response = table.scan()

    # Create a pretty table
    table = PrettyTable()
    table.field_names = [
        "Project ID",
        "Range Key",
        "IAC Stack Composite Key",
        "Created By",
        "Created At",
        "Status",
        "Status Reason",
        "Configuration",
        "Deployments",
    ]

    # Add the items to the table
    for item in response["Items"]:
        table.add_row(
            [
                item["project_id"],
                item["range_key"],
                item.get("iac_stack_composite_key", None),
                item["created_by"],
                item["created_at"],
                item.get("status", None),
                item.get("status_reason", None),
                item["configuration"],
                item.get("deployments", None),
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

    # Query the table
    response = table.query(KeyConditionExpression=Key("project_id").eq(pack_id))

    # Create a pretty table
    table = PrettyTable()
    table.field_names = [
        "Project ID",
        "Range Key",
        "IAC Stack Composite Key",
        "Created By",
        "Created At",
        "Status",
        "Deployments",
        "Configuration",
    ]

    # Add the items to the table
    for item in response["Items"]:
        print(item["range_key"])
        if app_name in item["range_key"]:
            table.add_row(
                [
                    item["project_id"],
                    item["range_key"],
                    item.get("iac_stack_composite_key", None),
                    item["created_by"],
                    item["created_at"],
                    item.get("status", None),
                    item.get("deployments", None),
                    item["configuration"],
                ]
            )

    # Print the table
    print(table)


@dynamodb.command()
@click.option("--pack-id", prompt="Pack ID", help="The ID of the pack.")
@click.option("--range-key", prompt="App range key", help="The range key of the app.")
@click.option("--new-status", prompt="New status", help="The new status of the app.")
async def transition_user_app_status(pack_id, range_key, new_status):
    # Create a DynamoDB resource
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")

    # Get the table
    table = dynamodb.Table("AppDeployments")

    # Query the table to get the item
    response = table.query(KeyConditionExpression=Key("project_id").eq(pack_id))
    items = response.get("Items")

    if not items:
        print(f"No app found with ID: {range_key}")
        return

    item = [i for i in items if i["range_key"] == range_key][0]
    # Update the status of the app
    item["status"] = new_status

    # Update the item in the table
    table.put_item(Item=item)

    print(f"Status of app '{range_key}' updated to '{new_status}'.")


@dynamodb.command()
@click.option("--table-name", prompt="Table name", help="The name of the table.")
@click.option("--field-name", prompt="Field name", help="The name of the field.")
async def transition_set_to_list(table_name, field_name):
    # Create a DynamoDB resource
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")

    # Get the table
    table = dynamodb.Table(table_name)

    def convert_set_to_list(item):
        if field_name in item and isinstance(item[field_name], set):
            item[field_name] = list(item[field_name])
            return item

    # Scan the table and update items
    table = dynamodb.Table(table_name)
    response = table.scan()
    for item in response["Items"]:
        updated_item = convert_set_to_list(item)
        if updated_item:
            table.put_item(Item=updated_item)
