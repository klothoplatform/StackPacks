import json
import os
from datetime import datetime
from urllib.parse import urlencode

import boto3
import requests

session = boto3.session.Session()


class CloudWatchAlarmParser:
    def __init__(self, msg):
        self.msg = msg
        self.timestamp_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        self.trigger = msg["Trigger"]

        if self.msg["NewStateValue"] == "ALARM":
            self.color = "danger"
        elif self.msg["NewStateValue"] == "OK":
            self.color = "good"

    def __url(self):
        return (
            "https://console.aws.amazon.com/cloudwatch/home?"
            + urlencode({"region": session.region_name})
            + "#alarmsV2:alarm/"
            + self.msg["AlarmName"]
        )

    def slack_data(self):
        _message = {
            "text": "<!here|here>",
            "attachments": [
                {
                    "title": "AWS CloudWatch Notification",
                    "ts": datetime.strptime(
                        self.msg["StateChangeTime"], self.timestamp_format
                    ).timestamp(),
                    "color": self.color,
                    "fields": [
                        {
                            "title": "Alarm Name",
                            "value": self.msg["AlarmName"],
                            "short": True,
                        },
                        {
                            "title": "Alarm Description",
                            "value": self.msg["AlarmDescription"],
                            "short": False,
                        },
                        {
                            "title": "Trigger",
                            "value": " ".join(
                                [
                                    self.trigger["Statistic"],
                                    self.trigger["MetricName"],
                                    self.trigger["ComparisonOperator"],
                                    str(self.trigger["Threshold"]),
                                    "for",
                                    str(self.trigger["EvaluationPeriods"]),
                                    "period(s) of",
                                    str(self.trigger["Period"]),
                                    "seconds.",
                                ]
                            ),
                            "short": False,
                        },
                        {
                            "title": "Old State",
                            "value": self.msg["OldStateValue"],
                            "short": True,
                        },
                        {
                            "title": "Current State",
                            "value": self.msg["NewStateValue"],
                            "short": True,
                        },
                        {
                            "title": "Link to Alarm",
                            "value": self.__url(),
                            "short": False,
                        },
                    ],
                }
            ],
        }
        return _message


def lambda_handler(event, context):

    sns_message = json.loads(event["Records"][0]["Sns"]["Message"])
    print(sns_message)

    alarm_state_only: list = json.loads(os.environ.get("ALARM_STATE_ONLY", "[]"))

    if sns_message["NewStateValue"] == "OK" or (
        sns_message["NewStateValue"] == "INSUFFICIENT_DATA"
        and sns_message["AlarmName"] in alarm_state_only
    ):
        return {
            "statusCode": 200,
            "body": "OK",
        }

    webhook_url = "https://hooks.slack.com/services/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"

    slack_data = CloudWatchAlarmParser(sns_message).slack_data()
    slack_data["channel"] = "cloudwatch-alerts"

    response = requests.post(
        webhook_url,
        json=slack_data,
    )

    return {
        "statusCode": response.status_code,
        "body": response.content.decode("utf-8"),
    }
