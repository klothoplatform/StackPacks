from pathlib import Path
from typing import Any, List
from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_yaml import parse_yaml_file_as
from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
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


class CommonPack(dict[BaseRequirements, CommonPart]):
    def get_resources_from_requirements(
        self, requirements: List[BaseRequirements]
    ) -> Resources:
        resources = Resources()
        for requirement in requirements:
            resources.update(self[requirement].resources)
        return resources

    def get_edges_from_requirements(
        self, requirements: List[BaseRequirements]
    ) -> Edges:
        edges = Edges()
        for requirement in requirements:
            edges.update(self[requirement].edges)
        return edges

    def get_configuration_from_requirements(
        self, requirements: List[BaseRequirements]
    ) -> dict[str, StackConfig]:
        configuration = {}
        for requirement in requirements:
            configuration.update(self[requirement].configuration)
        return configuration

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(dict[BaseRequirements, CommonPart])

        non_instance_schema = core_schema.no_info_after_validator_function(
            CommonPack, sequence_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])


def get_stack_pack_base() -> CommonPack:
    root = Path("stackpacks_common")
    f = root / "common.yaml"
    base = parse_yaml_file_as(CommonPack, f)
    return base


class CommonStack(StackPack):

    def __init__(self, stack_packs: List[StackPack]):

        base = get_stack_pack_base()
        # Initialize an empty StackParts object
        resources = Resources()
        edges = Edges()
        configuration = {}

        requirements = set()
        # find all required base parts
        for stack_pack in stack_packs:
            for requirement in stack_pack.requires:
                requirements.add(requirement)

        dependencies = set()

        for requirement in requirements:
            base_part = base[requirement]
            resources.update(base_part.resources)
            edges.update(base_part.edges)
            configuration.update(base_part.configuration)
            dependencies.update(base_part.depends_on)

        for requirement in dependencies:
            base_part = base[requirement]
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
