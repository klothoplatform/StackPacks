from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from pydantic_yaml import parse_yaml_file_as

from src.project import (
    BaseRequirements,
    ConfigValues,
    DockerImage,
    Edges,
    Resources,
    StackConfig,
    StackPack,
    StackParts,
)


class Feature(Enum):
    HEALTH_MONITOR = "health_monitor"

    @classmethod
    def default_features(cls):
        """Default features to include in the project / common stack.
        This must be kept in sync with the fields in StackRequest and any other places
        which influence the features in a project.
        """
        return [cls.HEALTH_MONITOR.value]


class CommonPart(BaseModel):
    depends_on: List[BaseRequirements | Feature] = []
    always_inject: List[str] = []
    never_inject: List[str] = []
    resources: Resources = Field(default_factory=Resources)
    edges: Edges = Field(default_factory=Edges)
    files: dict[str, Optional[dict]] = Field(default_factory=dict)
    configuration: dict[str, StackConfig] = Field(default_factory=dict)
    additional_policy: dict = Field(default_factory=dict)


class CommonBase(dict[BaseRequirements | Feature, CommonPart]):
    model_config = ConfigDict(
        extra="allow",  # required to allow non-BaseRequirements or Feature keys
    )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(
            dict[BaseRequirements | Feature, CommonPart]
        )

        non_instance_schema = core_schema.no_info_after_validator_function(
            CommonBase, sequence_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])


class CommonPack(BaseModel):
    id: str
    version: str
    docker_images: dict[str, DockerImage | None] = field(default_factory=dict)
    base: CommonBase


def parse_raw_pack() -> CommonPack:
    root = Path("stackpacks_common")
    f = root / "common.yaml"
    pack = parse_yaml_file_as(CommonPack, f)
    return pack


class CommonStack(StackPack):
    COMMON_APP_NAME: ClassVar[str] = "common"

    always_inject: Set[str] = Field(default_factory=set)
    never_inject: Set[str] = Field(default_factory=set)
    additional_policies: List[dict] = Field(default_factory=list)

    def __init__(self, stack_packs: List[StackPack], features: List[str]):

        pack = parse_raw_pack()
        base = pack.base
        # Initialize an empty StackParts object
        resources = Resources()
        edges = Edges()
        configuration = {}
        files = {}
        always_inject = set()
        never_inject = set()
        additional_policies = []

        requirements = set()
        # find all required base parts
        for stack_pack in stack_packs:
            for requirement in stack_pack.requires:
                requirements.add(requirement)

        dependencies = set()

        def add_dependencies(base_part: CommonPart):
            always_inject.update(base_part.always_inject)
            never_inject.update(base_part.never_inject)
            if base_part.additional_policy:
                additional_policies.append(base_part.additional_policy)
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
            additional_policies=additional_policies,
            id=pack.id,
            name=CommonStack.COMMON_APP_NAME,
            version=pack.version,
            requires=[],
            base=stack_base,
            configuration=configuration,
            docker_images=pack.docker_images,
        )

    def copy_files(
        self, user_config: ConfigValues, out_dir: Path, root: Path | None = None
    ):
        if root is None:
            root = Path("stackpacks_common")
        super().copy_files(user_config, out_dir, root)
