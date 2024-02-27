import os
import re
from typing import List
from pydantic import BaseModel
import datetime
from enum import Enum
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute


class DeploymentStatus(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class DeploymentAction(Enum):
    DEPLOY = "DEPLOY"
    REFRESH = "REFRESH"
    DESTROY = "DESTROY"


class Deployment(Model):

    class Meta:
        table_name = "Deployments"
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)

    id: str = UnicodeAttribute(hash_key=True)
    iac_stack_composite_key: str = UnicodeAttribute(range_key=True)
    action: str = UnicodeAttribute()
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute()
    initiated_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )
    initiated_by: str = UnicodeAttribute()

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Deployment):
            return False
        return (
            self.id == __value.id
            and self.iac_stack_key == __value.iac_stack_key
            and self.action == __value.action
            and self.status == __value.status
            and self.status_reason == __value.status_reason
            and self.initiated_at == __value.initiated_at
            and self.initiated_by == __value.initiated_by
        )


class PulumiStack(Model):
    class Meta:
        table_name = "PulumiStacks"
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)

    project_name: str = UnicodeAttribute(hash_key=True)
    name: str = UnicodeAttribute(range_key=True)
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute()
    created_at: datetime.datetime = UTCDateTimeAttribute(
        default=datetime.datetime.now()
    )
    created_by: str = UnicodeAttribute()

    def composite_key(self):
        return f"{self.project_name}#{self.name}"

    @staticmethod
    def sanitize_stack_name(stack_name):
        return re.sub(r"[^a-zA-Z0-9\-_.]", "_", stack_name)

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, PulumiStack):
            return False
        return (
            self.name == __value.name
            and self.project_name == __value.project_name
            and self.status == __value.status
            and self.status_reason == __value.status_reason
            and self.created_at == __value.created_at
            and self.created_by == __value.created_by
        )
