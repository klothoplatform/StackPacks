import json
import os

import boto3

from src.util.logging import logger

# The subject line for the email.
SUBJECT = "StackSnapDeployment"

# The email body for recipients with non-HTML email clients.
BODY_TEXT = (
    "Amazon SES Test (Python)\r\n"
    "This email was sent with Amazon SES using the "
    "AWS SDK for Python (Boto)."
)

# The HTML body of the email.
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Amazon SES Test (SDK for Python)</h1>
  <p>This email was sent with
    <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
    <a href='https://aws.amazon.com/sdk-for-python/'>
      AWS SDK for Python (Boto)</a>.</p>
</body>
</html>
            """

# The character encoding for the email.
CHARSET = "UTF-8"


def send_email(client: boto3.client, recipient: str, applications: list[str]):
    # This address must be verified with Amazon SES.
    sender_address = os.getenv("SES_SENDER_ADDRESS", None)
    sender = f"Stack Snap <{sender_address}>"

    if not sender_address:
        logger.error("No sender address set. Cannot send email.")
        return
    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            FromEmailAddress=sender,
            Destination={
                "ToAddresses": [
                    recipient,
                ],
            },
            Content={
                "Simple": {
                    "Subject": {
                        "Charset": CHARSET,
                        "Data": SUBJECT,
                    },
                    "Body": {
                        "Html": {
                            "Charset": CHARSET,
                            "Data": BODY_HTML,
                        },
                        "Text": {
                            "Charset": CHARSET,
                            "Data": "StackSnap\r\n"
                            "We have successfully deployed the following applications: \r\n"
                            f"{', '.join(applications)}",
                        },
                    },
                },
            },
        )
    # Display an error if something goes wrong.
    except Exception as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),


def send_klotho_engineering_email(client: boto3.client, message: str):
    # This address must be verified with Amazon SES.
    sender_address = os.getenv("SES_SENDER_ADDRESS", None)
    sender = f"Stack Snap <{sender_address}>"

    if not sender_address:
        logger.error("No sender address set. Cannot send email.")
        return
    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            FromEmailAddress=sender,
            Destination={
                "ToAddresses": [
                    "klotho-engineering@klo.dev",
                ],
            },
            Content={
                "Simple": {
                    "Subject": {
                        "Charset": CHARSET,
                        "Data": "SnackStap Customer Alarm",
                    },
                    "Body": {
                        "Text": {
                            "Charset": CHARSET,
                            "Data": json.dumps(message, indent=4),
                        },
                    },
                },
            },
        )
    # Display an error if something goes wrong.
    except Exception as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),
