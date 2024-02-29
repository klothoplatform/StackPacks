import os
import re
from pydantic import BaseModel
import datetime
from enum import Enum
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    JSONAttribute,
)


class UserPack(Model):
    class Meta:
        table_name = "UserPacks"
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)

    user_id: str = UnicodeAttribute(hash_key=True)
    # Configuration is a dictionary where the keys are the oss package
    # and the value is another dictionary of the key value configurations for that oss package
    configuration: dict = JSONAttribute()
    iac_stack_composite_key: str = UnicodeAttribute()

    def update_configurations(self, configuration: dict):
        self.update(actions=[UserPack.configuration.set(configuration)])
