from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from pydantic_yaml import parse_yaml_file_as

from src.stack_pack import (
    StackConfig,
    StackPack,
    StackParts,
    Resources,
    Edges,
    ConfigValues,
    BaseRequirements,
)


class CommonPart(BaseModel):
    depends_on: List[BaseRequirements] = []
    resources: Resources = Field(default_factory=Resources)
    edges: Edges = Field(default_factory=Edges)
    configuration: dict[str, StackConfig] = Field(default_factory=dict)


class CommonPack(BaseModel):
    base: dict[BaseRequirements, CommonPart] = Field(default_factory=dict)

    def get_resources_from_requirements(
        self, requirements: List[BaseRequirements]
    ) -> Resources:
        resources = Resources()
        for requirement in requirements:
            resources.update(self.base[requirement].resources)
        return resources

    def get_edges_from_requirements(
        self, requirements: List[BaseRequirements]
    ) -> Edges:
        edges = Edges()
        for requirement in requirements:
            edges.update(self.base[requirement].edges)
        return edges

    def get_configuration_from_requirements(
        self, requirements: List[BaseRequirements]
    ) -> dict[str, StackConfig]:
        configuration = {}
        for requirement in requirements:
            configuration.update(self.base[requirement].configuration)
        return configuration


def get_stack_pack_base() -> CommonPack:
    root = Path("stackpacks_base")
    f = root / "base.yaml"
    print(f)
    base = parse_yaml_file_as(CommonPack, f)
    print(base)
    return base


class CommonStack(StackPack):

    def __init__(self, stack_packs: List[StackPack]):

        print("getting base")
        base = get_stack_pack_base()
        # Initialize an empty StackParts object
        resources = Resources()
        edges = Edges()
        configuration = {}

        requirements = set()
        # find all required base parts
        for stack_pack in stack_packs:
            for requirement in stack_pack.requires:
                requirements.add(requirement.value)

        dependencies = set()

        print(base.base)
        for requirement in requirements:
            print(requirement, base.base.keys())
            base_part = base.base[requirement]
            resources.update(base_part.resources)
            edges.update(base_part.edges)
            configuration.update(base_part.configuration)
            dependencies.update(base_part.depends_on)

        for requirement in dependencies:
            base_part = base.base[requirement]
            resources.update(base_part.resources)
            edges.update(base_part.edges)
            configuration.update(base_part.configuration)

        stack_base = StackParts(resources=resources, edges=edges)
        super().__init__(
            id="base",
            name="base",
            version="0.0.1",
            requires=[],
            base=stack_base,
            configuration=configuration,
        )

    def to_constraints(self, user_config: ConfigValues) -> List[dict]:
        constraints = super().to_constraints(user_config)

        for c in constraints:
            if c["scope"] == "application" and c["operator"] == "must_exist":
                c["operator"] = "import"
        return constraints
