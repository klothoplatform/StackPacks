from pulumi import automation as auto
from pydantic_yaml import parse_yaml_raw_as

from src.engine_service.engine_commands.get_live_state import (
    GetLiveStateRequest,
    get_live_state,
)
from src.stack_pack.live_state import LiveState
from src.util.tmp import TempDir


class AppManager:
    def __init__(self, stack: auto.Stack):
        self.stack = stack

    async def read_deployed_state(self) -> LiveState:
        resources = self.stack.export_stack().deployment["resources"]
        tmp_dir = TempDir()
        resources_yaml = await get_live_state(
            GetLiveStateRequest(state=resources, tmp_dir=tmp_dir.dir)
        )
        live_state = parse_yaml_raw_as(LiveState, resources_yaml)
        tmp_dir.cleanup()
        return live_state

    def get_outputs(self, outputs: dict[str, str]) -> dict[str, str]:
        result: dict[str, str] = {}
        stack_outputs = self.stack.outputs()
        print(stack_outputs)
        for name, output in outputs.items():
            print(name, output)
            result[name] = stack_outputs[output].value
        return result
