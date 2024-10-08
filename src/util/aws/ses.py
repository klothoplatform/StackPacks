import json
import os
from typing import Optional

import boto3
from botocore.exceptions import EndpointConnectionError, HTTPClientError
from pydantic import BaseModel

from src.util.logging import logger

# The subject line for the email.
SUBJECT = "StackSnapDeployment"

# The character encoding for the email.
CHARSET = "UTF-8"


def create_app_data(app_name: str, login_url: str):
    return (
        f"Application Name: {app_name}\n" + f"Login URL: {login_url}\n"
        if login_url
        else ""
    )


class AppData(BaseModel):
    app_name: str
    login_url: Optional[str]

    def to_html(self):
        return create_app_data(self.app_name, self.login_url)

    def to_text(self):
        return create_app_data(self.app_name, self.login_url)


def create_installation_body_html(apps: list[AppData]):
    app_data = "\n".join([a.to_html() for a in apps])
    app_names = ", ".join([a.app_name for a in apps])

    return f"""
    <h3>Hello!</h3>
    <p>StackSnap finished installing {app_names}!</p>
    {app_data}
    <p>To keep your software secure, we do not email passwords.</p>
    <p>We're working on adding nicer URLs and custom domains — that’s coming soon!</p>
    <h2>Support and Community</h2>
    <p>Join us on our <a href="https://klo.dev/discordurl">discord</a> to ask for features, chat with the team or ask for support! We're happy to help!</p>
    <p>Thanks again!<br>StackSnap team</p>
    <p><i>NOTE: StackSnap is just an automatic software installer and does not provide any support for the individual software packages. Please visit the software vendor's website for support.</i></p>
    """


def create_installation_body_text(apps: list[AppData]):
    app_data = "\n".join([a.to_text() for a in apps])
    app_names = ", ".join([a.app_name for a in apps])

    return f"""
    Hello!
    StackSnap finished installing {app_names}!
    {app_data}
    To keep your software secure, we do not email passwords.
    We're working on adding nicer URLs and custom domains - that’s coming soon!
    Support and Community
    Join us on our discord to ask for features, chat with the team or ask for support! We're happy to help!
    Thanks again!
    StackSnap team
    NOTE: StackSnap is just an automatic software installer and does not provide any support for the individual software packages. Please visit the software vendor's website for support.
    """


def send_deployment_success_email(
    client: boto3.client, recipient: str, applications: list[AppData]
):
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
                            "Data": create_installation_body_html(applications),
                        },
                        "Text": {
                            "Charset": CHARSET,
                            "Data": create_installation_body_text(applications),
                        },
                    },
                },
            },
        )
    # Display an error if something goes wrong.
    except HTTPClientError as e:
        logger.error(e.response["Error"]["Message"])
    except Exception as e:
        logger.error("Sending email failed!", exc_info=True)
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),


def send_klotho_engineering_email(client: boto3.client, message: str):
    # This address must be verified with Amazon SES.
    sender_address = os.getenv("SES_SENDER_ADDRESS", None)
    sender = f"Stack Snap <{sender_address}>"
    if not sender_address:
        logger.error("No sender address set. Cannot send email.")
        return
    logger.info(f"Sending email to Klotho Engineering from {sender}")
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
                        "Data": "StackSnap Customer Alarm",
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
        logger.error(e, exc_info=True)
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),
