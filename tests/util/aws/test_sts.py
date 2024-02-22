import aiounittest
from moto import mock_aws
import boto3
from src.util.aws.sts import (
    assume_role,
    AssumeRoleCredentials,
    AssumedRoleUser,
)  # replace with your actual module name


class TestAssumeRole(aiounittest.AsyncTestCase):
    @mock_aws
    async def test_assume_role(self):
        # Mock the sts_client.assume_role method
        sts_client = boto3.client("sts")
        sts_client.assume_role = lambda RoleArn, RoleSessionName: {
            "Credentials": {
                "AccessKeyId": "test_access_key_id",
                "SecretAccessKey": "test_secret_access_key",
                "SessionToken": "test_session_token",
                "Expiration": "test_expiration",
            },
            "AssumedRoleUser": {
                "Arn": "test_arn",
                "AssumedRoleId": "test_assumed_role_id",
            },
        }

        # Call the function to test
        assume_role_creds, assumed_role_user = assume_role(sts_client, "test_role_arn")

        # Check that the function returned the correct objects
        self.assertEqual(
            assume_role_creds,
            AssumeRoleCredentials(
                AccessKeyId="test_access_key_id",
                SecretAccessKey="test_secret_access_key",
                SessionToken="test_session_token",
                Expiration="test_expiration",
            ),
        )
        self.assertEqual(
            assumed_role_user,
            AssumedRoleUser(Arn="test_arn", AssumedRoleId="test_assumed_role_id"),
        )
