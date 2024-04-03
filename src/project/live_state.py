from typing import Optional

from pydantic import BaseModel, Field

from src.project import ConfigValues, Edges, Resources
from src.project.common_stack import CommonStack
from src.util.logging import logger


class LiveState(BaseModel):
    resources: Resources = Field(default_factory=Resources)
    edges: Optional[Edges] = Field(default_factory=Edges)

    def to_constraints(self, common_stack: CommonStack, configuration: ConfigValues):
        constraints = []

        for res, properties in common_stack.base.resources.items():
            current_properties = self.resources.get(res)
            if current_properties is not None and properties is not None:
                current_properties.update(properties)
                self.resources.update({res: current_properties})

        for r, properties in common_stack.base.resources.items():
            if r in common_stack.always_inject:
                logger.info(f"Adding from common resource {r} due to always inject")
                self.resources.update({r: properties})

        resources_from_state = Resources(
            {
                r: properties
                for r, properties in self.resources.items()
                if r not in common_stack.never_inject
            }
        )

        for c in resources_from_state.to_constraints(ConfigValues({})):
            if c["scope"] == "application" and c["operator"] == "must_exist":
                logger.info(f"Adding import constraint from live state resource {c}")
                c["operator"] = "import"
            constraints.append(c)
        if self.edges:
            constraints.extend(self.edges.to_constraints())

        for c in common_stack.base.edges.to_constraints():
            source = c["target"]["source"]
            target = c["target"]["target"]
            if (
                resources_from_state.get(target, None) is not None
                and resources_from_state.get(source, None) is not None
            ):
                constraints.append(c)

        for edge, key in common_stack.base.edges.items():
            if edge in common_stack.always_inject:
                logger.info(f"Adding from common edge {edge} due to always inject")
                constraints.extend(Edges({edge: key}).to_constraints())

        return constraints
