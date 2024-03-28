from datetime import datetime, timezone
import os
import re

from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.models import Model


class PulumiStack(Model):
    class Meta:
        table_name = os.environ.get("PULUMISTACKS_TABLE_NAME", "PulumiStacks")
        billing_mode = "PAY_PER_REQUEST"
        host = os.environ.get("DYNAMODB_HOST", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    project_name: str = UnicodeAttribute(hash_key=True)
    name: str = UnicodeAttribute(range_key=True)
    status: str = UnicodeAttribute()
    status_reason: str = UnicodeAttribute()
    created_at: datetime = UTCDateTimeAttribute(
        default=lambda: datetime.now(timezone.utc)
    )
    created_by: str = UnicodeAttribute()

    def composite_key(self):
        return f"{self.project_name}#{self.name}"

    @staticmethod
    def split_composite_key(composite_key) -> tuple[str, str]:
        split_key = composite_key.split("#")
        return split_key[0], split_key[1]

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
