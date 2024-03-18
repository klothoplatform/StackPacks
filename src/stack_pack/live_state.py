from typing import Optional

from pydantic import BaseModel, Field

from src.stack_pack import ConfigValues, Edges, Resources
from src.stack_pack.common_stack import CommonStack
from src.util.logging import logger


class LiveState(BaseModel):
    resources: Resources = Field(default_factory=Resources)
    edges: Optional[Edges] = Field(default_factory=Edges)

    def to_constraints(self, common_stack: CommonStack, configuration: ConfigValues):
        constraints = []

        for res, properties in common_stack.base.resources.items():
            if self.resources.get(res, None) is not None:
                self.resources[res].update(properties)

        for r, properties in common_stack.base.resources.items():
            if r in common_stack.always_inject:
                self.resources.update({r: properties})

        for c in self.resources.to_constraints(ConfigValues({})):
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
                self.resources.get(target, None) is not None
                and self.resources.get(source, None) is not None
            ):
                constraints.append(c)

        return constraints
