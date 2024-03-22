from unittest.mock import Mock

import aiounittest

from src.stack_pack import ConfigValues, Edges, Properties, Resources
from src.stack_pack.common_stack import CommonStack
from src.stack_pack.live_state import LiveState


class TestLiveState(aiounittest.AsyncTestCase):
    def test_to_constraints(self):
        # Arrange
        live_state = LiveState(
            resources=Resources(
                {
                    "resource1": Properties({}),
                    "resource2": Properties({"Property2": "Value2"}),
                }
            ),
            edges=Edges(),
        )
        stack_pack = Mock(
            spec=CommonStack,
            base=Mock(
                resources=Resources(
                    {
                        "resource1": Properties({"Property1": "Value1"}),
                        "resource2": Properties({"Property2": "Value2"}),
                    }
                ),
                edges=Edges({"resource1->resource2": None}),
            ),
            always_inject={},
            never_inject={},
        )
        configuration = ConfigValues()

        # Act
        result = live_state.to_constraints(stack_pack, configuration)

        # Assert
        expected_result = [
            {"scope": "application", "operator": "import", "node": "resource1"},
            {"scope": "application", "operator": "import", "node": "resource2"},
            {
                "scope": "resource",
                "operator": "equals",
                "property": "Property1",
                "value": "Value1",
                "target": "resource1",
            },
            {
                "scope": "resource",
                "operator": "equals",
                "property": "Property2",
                "value": "Value2",
                "target": "resource2",
            },
            {
                "scope": "edge",
                "operator": "must_exist",
                "target": {"source": "resource1", "target": "resource2"},
            },
        ]
        self.assertEqual(result, expected_result)

    def test_always_inject(self):
        # Arrange
        live_state = LiveState(
            resources=Resources(
                {
                    "aws:lambda_function:default": Properties({}),
                }
            ),
            edges=Edges(),
        )
        stack_pack = Mock(
            spec=CommonStack,
            base=Mock(
                resources=Resources(
                    {
                        "aws:region:region": Properties({"Property1": "Value1"}),
                    }
                ),
                edges=Edges({"resource1->resource2": None}),
            ),
            always_inject={"aws:region:region", "resource1->resource2"},
            never_inject={},
        )
        configuration = ConfigValues()

        # Act
        result = live_state.to_constraints(stack_pack, configuration)

        # Assert
        expected_result = [
            {
                "scope": "application",
                "operator": "import",
                "node": "aws:lambda_function:default",
            },
            {"scope": "application", "operator": "import", "node": "aws:region:region"},
            {
                "scope": "resource",
                "operator": "equals",
                "property": "Property1",
                "value": "Value1",
                "target": "aws:region:region",
            },
            {
                "operator": "must_exist",
                "scope": "edge",
                "target": {"source": "resource1", "target": "resource2"},
            },
        ]
        self.assertEqual(result, expected_result)

    def test_never_inject(self):
        # Arrange
        live_state = LiveState(
            resources=Resources(
                {
                    "aws:lambda_function:default": Properties({}),
                }
            ),
            edges=Edges(),
        )
        stack_pack = Mock(
            spec=CommonStack,
            base=Mock(
                resources=Resources(
                    {
                        "aws:region:region": Properties({"Property1": "Value1"}),
                    }
                ),
                edges=Edges({"resource1->resource2": None}),
            ),
            always_inject={},
            never_inject={"aws:lambda_function:default"},
        )
        configuration = ConfigValues()

        # Act
        result = live_state.to_constraints(stack_pack, configuration)

        # Assert
        expected_result = []
        self.assertEqual(result, expected_result)
