from pulumi import automation as auto
from src.stack_pack.live_state import LiveState
from src.engine_service.engine_commands.get_live_state import get_live_state, GetLiveStateRequest
from pydantic_yaml import parse_yaml_raw_as

from src.util.tmp import TempDir

class AppManager:
    def __init__(self, stack: auto.Stack):
        self.stack = stack

    async def read_deployed_state(self) -> LiveState:
        resources = self.stack.export_stack().deployment["resources"]
        tmp_dir = TempDir()
        resources_yaml = await get_live_state(GetLiveStateRequest(
            state=resources,
            tmp_dir=tmp_dir.dir
        ))
        live_state = parse_yaml_raw_as(LiveState, resources_yaml)
        tmp_dir.cleanup()
        return live_state
