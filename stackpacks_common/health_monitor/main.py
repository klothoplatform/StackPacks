import json
import os

import requests


def lambda_handler(event, context):

    pack_id: str = os.environ.get("PACK_ID", "pack_id")
    health_endpoint_url = os.environ.get("HEALTH_ENDPOINT_URL", "http://localhost:3000")
    print("pack_id: " + pack_id)
    print("health_endpoint_url: " + health_endpoint_url)
    print(event)
    for record in event["Records"]:
        print("test")
        payload = record
        print(str(payload))

    message: dict = json.loads(event["Records"][0]["Sns"]["Message"])
    print("From SNS: " + event["Records"][0]["Sns"]["Message"])
    payload = {
        "OldStateValue": message.get("OldStateValue"),
        "NewStateValue": message.get("NewStateValue"),
        "AlarmArn": message.get("AlarmArn"),
        "StateChangeTime": message.get("StateChangeTime"),
        "PackId": pack_id,
    }
    response = requests.post(
        f"{health_endpoint_url}/api/health",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    print(response.status_code)
    return message
