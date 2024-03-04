import json


class Policy:
    def __init__(self, policy_string: str):
        self.policy = json.loads(policy_string)

    def combine(self, other_policy):
        self.policy["Statement"].extend(other_policy.policy["Statement"])

    def __str__(self):
        return json.dumps(self.policy, indent=4)
