import json
import logging
import os
import sys

import requests

# Create a custom logger
logger = logging.getLogger(__name__)

# Create handlers and formatters
c_handler = logging.StreamHandler(sys.stdout)
file_handler = None

c_format = logging.Formatter(
    "%(name)s - %(pathname)s - %(lineno)d - %(levelname)s - %(asctime)s - %(message)s"
)
c_handler.setFormatter(c_format)

log_handlers = [c_handler]

# Add handlers to the logger
logger.handlers = log_handlers
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):

    pack_id: str = os.environ.get("PACK_ID", "pack_id")
    health_endpoint_url = os.environ.get("HEALTH_ENDPOINT_URL", "http://localhost:3000")

    message: dict = json.loads(event["Records"][0]["Sns"]["Message"])
    logger.info("From SNS: " + event["Records"][0]["Sns"]["Message"])
    payload = {
        "OldStateValue": message.get("OldStateValue"),
        "NewStateValue": message.get("NewStateValue"),
        "AlarmArn": message.get("AlarmArn"),
        "StateChangeTime": message.get("StateChangeTime"),
        "PackId": pack_id,
    }
    logger.info("Payload: " + json.dumps(payload))
    logger.info(f"Sending post request to {health_endpoint_url}/api/health")
    response = requests.post(
        f"{health_endpoint_url}/api/health",
        json=payload,
    )
    logger.info(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        logger.info("Failed to send health message")
        logger.info(response.text)
    return message
