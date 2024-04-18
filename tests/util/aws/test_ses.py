import os
import unittest
from unittest.mock import MagicMock

from src.util.aws.ses import AppData, send_deployment_success_email


class TestSendEmail(unittest.TestCase):
    def test_send_email(self):
        os.environ["SES_SENDER_ADDRESS"] = "stacksnap@stacksnap.com"
        mock_client = MagicMock()
        mock_data = [
            AppData(app_name="app1", login_url="login1"),
            AppData(app_name="app2", login_url="login2"),
        ]
        send_deployment_success_email(mock_client, "recipient@example.com", mock_data)
        mock_client.send_email.assert_called_once_with(
            FromEmailAddress="Stack Snap <stacksnap@stacksnap.com>",
            Destination={"ToAddresses": ["recipient@example.com"]},
            Content={
                "Simple": {
                    "Subject": {"Charset": "UTF-8", "Data": "StackSnapDeployment"},
                    "Body": {
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": "\n    <h3>Hello!</h3>\n    <p>StackSnap finished installing app1, app2!</p>\n    Application Name: app1\nLogin URL: login1\n\nApplication Name: app2\nLogin URL: login2\n\n    <p>To keep your software secure, we do not email passwords.</p>\n    <p>We're working on adding nicer URLs and custom domains — that’s coming soon!</p>\n    <h2>Support and Community</h2>\n    <p>Join us on our <a href=\"https://klo.dev/discordurl\">discord</a> to ask for features, chat with the team or ask for support! We're happy to help!</p>\n    <p>Thanks again!<br>StackSnap team</p>\n    <p><i>NOTE: StackSnap is just an automatic software installer and does not provide any support for the individual software packages. Please visit the software vendor's website for support.</i></p>\n    ",
                        },
                        "Text": {
                            "Charset": "UTF-8",
                            "Data": "\n    Hello!\n    StackSnap finished installing app1, app2!\n    Application Name: app1\nLogin URL: login1\n\nApplication Name: app2\nLogin URL: login2\n\n    To keep your software secure, we do not email passwords.\n    We're working on adding nicer URLs and custom domains - that’s coming soon!\n    Support and Community\n    Join us on our discord to ask for features, chat with the team or ask for support! We're happy to help!\n    Thanks again!\n    StackSnap team\n    NOTE: StackSnap is just an automatic software installer and does not provide any support for the individual software packages. Please visit the software vendor's website for support.\n    ",
                        },
                    },
                }
            },
        )
