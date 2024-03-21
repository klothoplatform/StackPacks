from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Set

from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from pydantic_yaml import parse_yaml_file_as

from src.stack_pack import (
    BaseRequirements,
    ConfigValues,
    Edges,
    Resources,
    StackConfig,
    StackPack,
    StackParts,
)
from src.util.logging import logger


class Feature(Enum):
    HEALTH_MONITOR = "health_monitor"


class CommonPart(BaseModel):
    depends_on: List[BaseRequirements | Feature] = []
    always_inject: List[str] = []
    never_inject: List[str] = []
    resources: Resources = Field(default_factory=Resources)
    edges: Edges = Field(default_factory=Edges)
    files: dict[str, Optional[dict]] = Field(default_factory=dict)
    configuration: dict[str, StackConfig] = Field(default_factory=dict)


class CommonPack(dict[BaseRequirements | Feature, CommonPart]):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(
            dict[BaseRequirements | Feature, CommonPart]
        )

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

    always_inject: Set[str] = Field(default_factory=set)
    never_inject: Set[str] = Field(default_factory=set)

    def __init__(self, stack_packs: List[StackPack], features: List[str]):

        base = get_stack_pack_base()
        # Initialize an empty StackParts object
        resources = Resources()
        edges = Edges()
        configuration = {}
        files = {}
        always_inject = set()
        never_inject = set()

        requirements = set()
        # find all required base parts
        for stack_pack in stack_packs:
            for requirement in stack_pack.requires:
                requirements.add(requirement)

        dependencies = set()

        def add_dependencies(base_part: CommonPart):
            always_inject.update(base_part.always_inject)
            never_inject.update(base_part.never_inject)
            resources.update(base_part.resources)
            edges.update(base_part.edges)
            files.update(base_part.files)
            configuration.update(base_part.configuration)

        for requirement in requirements:
            base_part = base[requirement]
            add_dependencies(base_part)
            dependencies.update(base_part.depends_on)

        for requirement in dependencies:
            base_part = base[requirement]
            add_dependencies(base_part)

        for feature in features:
            feature = Feature(feature)
            base_part = base[feature]
            add_dependencies(base_part)

        stack_base = StackParts(files=files, resources=resources, edges=edges)
        super().__init__(
            always_inject=always_inject,
            never_inject=never_inject,
            id="base",
            name="base",
            version="0.0.1",
            requires=[],
            base=stack_base,
            configuration=configuration,
        )

    def copy_files(self, user_config: ConfigValues, out_dir: Path):

        root = Path("stackpacks_common")
        for f, data in self.base.files.items():
            logger.info("writing commons file: " + str(out_dir / f))
            (out_dir / f).write_bytes((root / f).read_bytes())
