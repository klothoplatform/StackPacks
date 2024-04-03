import os

from fastapi import APIRouter

from src.project import get_stack_packs, StackConfig

router = APIRouter()

SHOW_TEST_PACKS = os.getenv("SHOW_TEST_PACKS", "false").lower() == "true"


@router.get("/api/stackpacks")
async def list_stackpacks():
    sps = get_stack_packs()

    def config_to_dict(cfg: StackConfig):
        c = {
            "name": cfg.name,
            "description": cfg.description,
            "type": cfg.type,
            "secret": cfg.secret,
        }
        if cfg.default is not None:
            c["default"] = cfg.default
        if cfg.validation is not None:
            c["validation"] = cfg.validation
        if cfg.pulumi_key is not None:
            c["pulumi_key"] = cfg.pulumi_key
        return c

    return {
        spid: {
            "id": spid,
            "name": sp.name,
            "version": sp.version,
            "description": sp.description,
            "configuration": {
                k: config_to_dict(cfg) for k, cfg in sp.configuration.items()
            },
        }
        for spid, sp in sps.items()
        if SHOW_TEST_PACKS or not spid.startswith("test_")
    }
