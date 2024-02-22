from dataclasses import dataclass


@dataclass
class AssumeRoleCredentials:
    AccessKeyId: str
    SecretAccessKey: str
    SessionToken: str
    Expiration: str


@dataclass
class AssumedRoleUser:
    Arn: str
    AssumedRoleId: str


def assume_role(sts_client, role_arn) -> tuple[AssumeRoleCredentials, AssumedRoleUser]:
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName="StackPackSession"
    )

    credentials = assumed_role_object["Credentials"]

    assumeRoleCreds = AssumeRoleCredentials(
        AccessKeyId=credentials["AccessKeyId"],
        SecretAccessKey=credentials["SecretAccessKey"],
        SessionToken=credentials["SessionToken"],
        Expiration=credentials["Expiration"],
    )

    assumedRoleUser = AssumedRoleUser(
        Arn=assumed_role_object["AssumedRoleUser"]["Arn"],
        AssumedRoleId=assumed_role_object["AssumedRoleUser"]["AssumedRoleId"],
    )

    return tuple([assumeRoleCreds, assumedRoleUser])
