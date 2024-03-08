from typing import Optional

from pydantic import BaseModel, Field

from src.stack_pack import ConfigValues, Edges, Resources, StackPack
from src.util.logging import logger


class LiveState(BaseModel):
    resources: Resources = Field(default_factory=Resources)
    edges: Optional[Edges] = Field(default_factory=Edges)

    def to_constraints(self, stack_pack: StackPack, configuration: ConfigValues):
        constraints = []

        for r in stack_pack.base.resources:
            if "aws:region" in r:
                for res in self.resources:
                    if "aws:region" in res:
                        region_properties = self.resources.pop(res)
                        self.resources.update({r: region_properties})
                        break
        for c in self.resources.to_constraints(ConfigValues({})):
            if c["scope"] == "application" and c["operator"] == "must_exist":
                logger.info(f"Adding import constraint from live state resource {c}")
                c["operator"] = "import"
            constraints.append(c)
        if self.edges:
            constraints.extend(self.edges.to_constraints())

        for c in stack_pack.base.resources.to_constraints(configuration):
            if c["scope"] == "resource":
                constraints.append(c)
        for c in stack_pack.base.edges.to_constraints():
            source = c["target"]["source"]
            target = c["target"]["target"]
            if (
                self.resources.get(target, None) is not None
                and self.resources.get(source, None) is not None
            ):
                constraints.append(c)

        return constraints
