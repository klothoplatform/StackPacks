from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Any, Optional, List


class ConfigValues(dict[str, Any]):
    pass


class Properties(dict[str, Any]):
    def to_constraints(self, config: ConfigValues):
        def convert_value(v: Any):
            if isinstance(v, str):
                # Do a first pass to see if we're expanding a config value
                # verbatim, which can handle complext object values
                for cfg, cfgV in config.items():
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
                return [c for k, vv in v.items() for c in to_c(f"{p}.{k}", vv)]
            elif isinstance(v, list):
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
    files: dict[str, dict] = Field(default_factory=dict)

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
    validation: Any = Field(default=None)
    values: dict[str, Optional[StackParts]] = Field(default=None)
    pulumi_key: Optional[str] = Field(default=None)


class StackPack(BaseModel):
    name: str
    version: str
    base: StackParts = Field(default_factory=StackParts)
    configuration: dict[str, StackConfig] = Field(default_factory=dict)

    def to_constraints(self, config: ConfigValues):
        final_cfg = ConfigValues()
        for k, v in self.configuration.items():
            if v.default is not None:
                final_cfg[k] = v.default
        final_cfg.update(config)
        return self.base.to_constraints(final_cfg)
