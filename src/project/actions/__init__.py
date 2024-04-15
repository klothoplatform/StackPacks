from enum import Enum
from typing import Callable

from src.project import get_stack_pack
from src.project.live_state import LiveState
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project


class Action(Enum):
    CREATE_DATABASE = "create_database"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


def get_action(action: Action) -> Callable:
    if action == Action.CREATE_DATABASE:
        from src.project.actions.database import create_database

        return create_database
    raise ValueError(f"Action {action} not found")


def run_actions(app: AppDeployment, project: Project, live_state: LiveState):
    sp = get_stack_pack(app.app_id())
    actions = sp.get_actions(app.get_configurations())
    for action in actions:
        action_name, config_value, config_key = action
        action = Action(action_name)
        action_function = get_action(action)
        val = action_function(config_value, sp, project, live_state)
        app.configuration[f"{config_key}:output"] = val
        app.update(actions=[AppDeployment.configuration.set(app.configuration)])
