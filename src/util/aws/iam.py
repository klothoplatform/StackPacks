import json
from itertools import groupby


class Policy:
    def __init__(self, policy_string: str | None = None):
        if policy_string:
            self.policy = json.loads(policy_string)
        else:
            self.policy = {"Version": "2012-10-17", "Statement": []}

    def combine(self, other_policy):
        self.policy["Statement"].extend(other_policy.policy["Statement"])
        self.compact_policy()

    def compact_policy(self):
        items = set(
            (stmt["Effect"], stmt["Resource"], a)
            for stmt in self.policy["Statement"]
            if not stmt.get("Condition", {})
            for a in stmt["Action"]
        )
        groups = groupby(items, key=lambda e: (e[0], e[1]))
        statements = []
        for (effect, resource), actions in groups:
            actions = sorted(a for _, _, a in actions)
            stmt = {"Effect": effect, "Action": actions, "Resource": resource}
            statements.append(stmt)
        for stmt in self.policy["Statement"]:
            if "Condition" in stmt:
                statements.append(stmt)
        self.policy["Statement"] = statements

    def __str__(self):
        return json.dumps(self.policy, indent=4)
