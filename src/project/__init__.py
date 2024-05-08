import glob
import os
import secrets
import string
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from pydantic_yaml import parse_yaml_file_as

from src.util.logging import logger

AWS_ACCOUNT = os.environ.get("AWS_ACCOUNT")
ECR_SUFFIX = os.environ.get("ECR_SUFFIX", "")


class BaseRequirements(Enum):
    NETWORK = "network"
    ECS = "ecs"
    POSTGRES = "postgres"
    MYSQL = "mysql"


class Output(BaseModel):
    value: str
    description: str

    def value_string(self):
        parts = self.value.split(":")[-1].split("#")
        return "_".join(parts).replace("-", "_")


class ConfigValues(dict[str, Any]):

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(dict[str, Any])

        non_instance_schema = core_schema.no_info_after_validator_function(
            ConfigValues, sequence_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])


class Properties(dict[str, Any]):
    def to_constraints(self, config: ConfigValues):
        def convert_value(v: Any):
            if isinstance(v, str):
                # Do a first pass to see if we're expanding a config value
                # verbatim, which can handle complext object values
                for cfg, cfgV in config.items():
                    # if the value is a docker image reference, substitute the image name
                    if v.startswith("${docker_image:") and "$docker_images" in config:
                        return config["$docker_images"].get(v.split(":")[1][:-1])

                    # If the value is a config value, return the config value
                    if v == f"${{{cfg}}}":
                        return cfgV

                # Otherwise, do a string replace
                for cfg, cfgV in config.items():
                    v = v.replace(f"${{{cfg}}}", str(cfgV))
                return v
            elif isinstance(v, dict):
                return {convert_value(k): convert_value(v) for k, v in v.items()}
            elif isinstance(v, list):
                return [convert_value(i) for i in v]
            else:
                return v

        def to_c(p: str, v: Any) -> List[dict]:
            if isinstance(v, dict):
                # TODO: Find a way to know how to set constraints smarter or fix the engine
                if "constraint_top_level" in list(v.keys()):
                    v.pop("constraint_top_level")
                    logger.info(
                        f"generating constraint for {p} as it is a top level constraint"
                    )
                    return [
                        {
                            "scope": "resource",
                            "operator": "equals",
                            "property": convert_value(p),
                            "value": convert_value(v),
                        }
                    ]
                return [c for k, vv in v.items() for c in to_c(f"{p}.{k}", vv)]
            if isinstance(v, list):
                return [
                    {
                        "scope": "resource",
                        "operator": "add",
                        "property": convert_value(p),
                        "value": convert_value(v),
                    }
                ]
            else:
                return [
                    {
                        "scope": "resource",
                        "operator": "equals",
                        "property": convert_value(p),
                        "value": convert_value(v),
                    }
                ]

        return [c for p, v in self.items() for c in to_c(p, v)]

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(dict[str, Any])

        non_instance_schema = core_schema.no_info_after_validator_function(
            Properties, sequence_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])


class Resources(dict[str, Optional[Properties]]):
    def to_constraints(self, config: ConfigValues):
        return [
            *[
                {
                    "scope": "application",
                    "operator": "must_exist",
                    "node": r,
                }
                for r in self.keys()
            ],
            *[
                {
                    **c,
                    "target": r,
                }
                for r, p in self.items()
                if p
                for c in p.to_constraints(config)
            ],
        ]

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(dict[str, Optional[Properties]])

        non_instance_schema = core_schema.no_info_after_validator_function(
            Resources, sequence_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])


class Edges(dict[str, Any]):
    def to_constraints(self):
        return [
            {
                "scope": "edge",
                "operator": "must_exist",
                "target": {
                    "source": e.split("->")[0].strip(),
                    "target": e.split("->")[1].strip(),
                },
            }
            for e in self.keys()
        ]

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        sequence_t_schema = handler.generate_schema(dict[str, Any])

        non_instance_schema = core_schema.no_info_after_validator_function(
            Edges, sequence_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])


class StackParts(BaseModel):
    resources: Resources = Field(default_factory=Resources)
    edges: Edges = Field(default_factory=Edges)
    files: dict[str, Optional[dict]] = Field(default_factory=dict)

    def to_constraints(self, config: ConfigValues):
        return [
            *(self.resources.to_constraints(config) if self.resources else []),
            *(self.edges.to_constraints() if self.edges else []),
        ]

    @classmethod
    def merge(parts: List["StackParts"]):
        merged = StackParts()
        for p in parts:
            if p.resources:
                for r, props in p.resources.items():
                    merged.resources.setdefault(r, Properties()).update(props)
            if p.edges:
                merged.edges.update(p.edges)
            if p.files:
                for f, data in p.files.items():
                    merged.files.setdefault(f, dict()).update(data)
        return merged


class StackConfig(BaseModel):
    name: str
    description: str
    type: str
    default: Any = Field(default=None)
    secret: bool = Field(default=False)
    validation: Any = Field(default=None)
    values: dict[Any, Optional[StackParts]] = Field(default_factory=dict)
    pulumi_key: Optional[str] = Field(default=None)
    action: Optional[str] = Field(default=None)
    generate_default: bool = Field(default=False)
    hidden: Optional[bool] = Field(default=False)
    configurationDisabled: Optional[bool] = Field(default=False)


class DockerImage(BaseModel):
    Dockerfile: str = Field(default="Dockerfile")
    Context: str = Field(default="")


class StackPack(BaseModel):
    id: str
    name: str
    version: str = Field(default="0.0.1")
    description: str = Field(default="")
    requires: list[BaseRequirements] = Field(default_factory=list)
    base: StackParts = Field(default_factory=StackParts)
    configuration: dict[str, StackConfig] = Field(default_factory=dict)
    outputs: dict[str, Output] = Field(default_factory=dict)
    docker_images: dict[str, DockerImage | None] = Field(default_factory=dict)

    def final_config(self, user_config: ConfigValues):
        final_cfg = ConfigValues()
        for k, v in self.configuration.items():
            if v.default is not None:
                final_cfg[k] = v.default
            if v.generate_default and user_config.get(k) is None:
                validation = v.validation or {}
                length = min(
                    validation.get("maxLength", 16), validation.get("minLength", 16)
                )
                final_cfg[k] = generate_default(
                    length, charset=validation.get("charset", "alphanumeric")
                )
        final_cfg.update(user_config)
        return final_cfg

    def to_constraints(self, user_config: ConfigValues, region: str):
        config = self.final_config(user_config)
        config["$docker_images"] = self.get_docker_images(region)

        constraints = self.base.to_constraints(config)

        for k, v in config.items():
            cfg = self.configuration.get(k)
            if cfg is None:
                logger.debug(f"no configuration for {k}")
                continue
            if v in cfg.values:
                constraints.extend(cfg.values[v].to_constraints(config))
        return constraints

    def get_docker_images(self, region: str) -> dict[str, str]:
        return {
            k: f"{AWS_ACCOUNT}.dkr.ecr.{region}.amazonaws.com/{k if k == self.id else self.id + '-' + k }{ECR_SUFFIX}:{self.version}"
            for k in self.docker_images.keys()
        }

    def copy_files(
        self, user_config: ConfigValues, out_dir: Path, root: Path | None = None
    ):
        config = self.final_config(user_config)

        if root is None:
            root = Path("stackpacks") / self.id
        for pattern, data in self.base.files.items():
            # TODO execute template if `data` has template: true
            for f in glob.glob(str(root / pattern), recursive=True):
                f = Path(f)  # convert string to Path object
                if f.is_dir():  # check if f is a file
                    continue
                relative_path = f.relative_to(root)
                logger.info("writing file: " + str(out_dir / relative_path))
                (out_dir / relative_path).parent.mkdir(parents=True, exist_ok=True)
                (out_dir / relative_path).write_bytes(f.read_bytes())
        # TODO also read files from `configuration.X.values` based on config

    def get_pulumi_configs(self, user_config: ConfigValues) -> dict[str, str]:
        config = self.final_config(user_config)

        result = {}
        for k, v in self.configuration.items():
            if v.pulumi_key:
                result[v.pulumi_key] = config[k]

        return result

    def get_actions(self, config: ConfigValues) -> list[tuple[str, str, str]]:
        result = []
        config = self.final_config(config)
        for k, v in self.configuration.items():
            if v.action:
                result.append((v.action, config[k], k))
        return result


def get_stack_packs() -> dict[str, StackPack]:
    root = Path("stackpacks")
    sps = {}
    for dir in root.iterdir():
        f = dir / f"{dir.name}.yaml"
        try:
            sp = parse_yaml_file_as(StackPack, f)
        except Exception as e:
            raise ValueError(f"Failed to parse {dir.name}") from e

        if sp.id in sps:
            raise ValueError(f"Duplicate stack pack id: {sp.id}")

        sps[sp.id] = sp
    return sps


def get_stack_pack(id: str) -> StackPack:
    f = Path("stackpacks") / id / f"{id}.yaml"
    try:
        return parse_yaml_file_as(StackPack, f)
    except Exception as e:
        raise ValueError(f"Failed to parse {id}") from e


def get_app_name(app_id: str):
    if app_id and "#" in app_id:
        app_id = app_id.split("#")[1]
    pack = get_stack_packs().get(app_id)
    return pack.name if pack else app_id


def generate_default(length: int, charset: str = "alphanumeric"):
    match charset:
        case "alphanumeric" | None:
            return rand_alphanumeric_string(length)
        case "hex":
            return rand_hex_string(length)
        case _:
            raise ValueError(f"Unknown charset: {charset}")


def rand_alphanumeric_string(length: int):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def rand_hex_string(length: int):
    key = secrets.token_hex(length // 2)
    return key if length % 2 == 0 else key + secrets.choice(string.hexdigits)
