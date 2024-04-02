import unittest
from pathlib import Path

from pydantic_yaml import parse_yaml_file_as

from src.stack_pack import StackPack


class TestStackPack(unittest.TestCase):
    def setUp(self):
        with open(Path(__file__).parent / "test_pack.yaml") as f:
            self.sp = parse_yaml_file_as(StackPack, f)
        self.maxDiff = None

    def test_parse_yaml(self):
        self.assertEqual("Test Pack", self.sp.name)
        self.assertEqual("test", self.sp.description)
        self.assertEqual(4, len(self.sp.base.resources))
        self.assertEqual(2, len(self.sp.base.edges))
        self.assertEqual(2, len(self.sp.base.files))
        self.assertEqual(3, len(self.sp.configuration))

    def test_constraints(self):
        constraints = self.sp.to_constraints({})

        self.assertCountEqual(
            [
                {
                    "scope": "application",
                    "operator": "must_exist",
                    "node": "test:basic:test1",
                },
                {
                    "scope": "application",
                    "operator": "must_exist",
                    "node": "test:array_index:test2",
                },
                {
                    "scope": "application",
                    "operator": "must_exist",
                    "node": "test:config_value:test3",
                },
                {
                    "scope": "application",
                    "operator": "must_exist",
                    "node": "test:array_value:test4",
                },
                {
                    "scope": "resource",
                    "operator": "equals",
                    "property": "Prop1",
                    "value": "value",
                    "target": "test:basic:test1",
                },
                {
                    "scope": "resource",
                    "operator": "equals",
                    "property": "LoadBalancers[0].ContainerPort",
                    "value": 8065,
                    "target": "test:array_index:test2",
                },
                {
                    "scope": "resource",
                    "operator": "add",
                    "property": "LoadBalancers",
                    "value": [
                        {
                            "ContainerPort": 8080,
                        }
                    ],
                    "target": "test:array_index:test2",
                },
                {
                    "scope": "resource",
                    "operator": "equals",
                    "property": "Cpu",
                    "value": 512,  # The ${CPU} was replaced with the default configuration
                    "target": "test:config_value:test3",
                },
                {
                    "scope": "resource",
                    "operator": "add",
                    "property": "Environment",
                    "value": [
                        {"Name": "KEY1", "Value": "v1"},
                        {"Name": "KEY2", "Value": "v2"},
                    ],
                    "target": "test:array_value:test4",
                },
                {
                    "scope": "edge",
                    "operator": "must_exist",
                    "target": {
                        "source": "test:basic:test1",
                        "target": "test:array_index:test2",
                    },
                },
                {
                    "scope": "edge",
                    "operator": "must_exist",
                    "target": {
                        "source": "test:array_index:test2",
                        "target": "test:config_value:test3",
                    },
                },
            ],
            constraints,
        )

    def test_config_constraints(self):
        constraints = self.sp.to_constraints({"AddResource": True})

        self.assertIn(
            {
                "scope": "application",
                "operator": "must_exist",
                "node": "test:added_type:test5",
            },
            constraints,
        )
        self.assertIn(
            {
                "scope": "edge",
                "operator": "must_exist",
                "target": {
                    "source": "test:config_value:test3",
                    "target": "test:added_type:test5",
                },
            },
            constraints,
        )

    def test_config_override(self):
        constraints = self.sp.to_constraints({"CPU": 1024})

        self.assertIn(
            {
                "scope": "resource",
                "operator": "equals",
                "property": "Cpu",
                "value": 1024,  # The ${CPU} was replaced with user config
                "target": "test:config_value:test3",
            },
            constraints,
        )
        self.assertNotIn(
            {
                "scope": "resource",
                "operator": "equals",
                "property": "Cpu",
                "value": 512,  # The default configuration is not used
                "target": "test:config_value:test3",
            },
            constraints,
        )

    def test_pulumi_config(self):
        cfg = self.sp.get_pulumi_configs({})

        self.assertEqual({"klo:pulumi-config": "a value"}, cfg)

        cfg = self.sp.get_pulumi_configs({"PulumiConfig": "different value"})

        self.assertEqual({"klo:pulumi-config": "different value"}, cfg)
