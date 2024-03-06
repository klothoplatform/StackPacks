import aiounittest
from unittest.mock import Mock
from src.stack_pack.live_state import LiveState
from src.stack_pack import ConfigValues, Properties, StackPack, Resources, Edges


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
            spec=StackPack,
            base=Mock(
                resources=Resources(
                    {
                        "resource1": Properties({"Property1": "Value1"}),
                        "resource2": Properties({"Property2": "Value2"}),
                    }
                ),
                edges=Edges({"resource1->resource2": None}),
            ),
        )
        configuration = ConfigValues()

        # Mock the methods that will be called in to_constraints
        live_state.resources.to_constraints = Mock(
            return_value=[
                {"scope": "application", "operator": "must_exist", "node": "resource1"},
                {"scope": "application", "operator": "must_exist", "node": "resource2"},
            ]
        )
        live_state.edges.to_constraints = Mock(return_value=[])

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

    def test_region_substituted(self):
        # Arrange
        live_state = LiveState(
            resources=Resources(
                {
                    "aws:region:default": Properties({}),
                }
            ),
            edges=Edges(),
        )
        stack_pack = Mock(
            spec=StackPack,
            base=Mock(
                resources=Resources(
                    {
                        "aws:region:region": Properties({"Property1": "Value1"}),
                    }
                ),
                edges=Edges({"resource1->resource2": None}),
            ),
        )
        configuration = ConfigValues()

        # Act
        result = live_state.to_constraints(stack_pack, configuration)

        # Assert
        expected_result = [
            {"scope": "application", "operator": "import", "node": "aws:region:region"},
            {
                "scope": "resource",
                "operator": "equals",
                "property": "Property1",
                "value": "Value1",
                "target": "aws:region:region",
            },
        ]
        self.assertEqual(result, expected_result)
