import os
import unittest
from unittest.mock import MagicMock

from src.util.aws.ses import send_email


class TestSendEmail(unittest.TestCase):
    def test_send_email(self):
        os.environ["SES_SENDER_ADDRESS"] = "stacksnap@stacksnap.com"
        mock_client = MagicMock()
        send_email(mock_client, "recipient@example.com", ["app1", "app2"])
        mock_client.send_email.assert_called_once_with(
            FromEmailAddress="Stack Snap <stacksnap@stacksnap.com>",
            Destination={"ToAddresses": ["recipient@example.com"]},
            Content={
                "Simple": {
                    "Subject": {"Charset": "UTF-8", "Data": "StackSnapDeployment"},
                    "Body": {
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": "<html>\n<head></head>\n<body>\n  <h1>Amazon SES Test (SDK for Python)</h1>\n  <p>This email was sent with\n    <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the\n    <a href='https://aws.amazon.com/sdk-for-python/'>\n      AWS SDK for Python (Boto)</a>.</p>\n</body>\n</html>\n            ",
                        },
                        "Text": {
                            "Charset": "UTF-8",
                            "Data": "StackSnap\r\nWe have successfully deployed the following applications: \r\napp1, app2",
                        },
                    },
                }
            },
        )
