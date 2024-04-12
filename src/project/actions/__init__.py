from enum import Enum
from typing import Callable

from src.project.live_state import LiveState
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


def run_actions(actions: list[(str, str)], project: Project, live_state: LiveState):
    for action in actions:
        action_name, action_data = action
        action = Action(action_name)
        action_function = get_action(action)
        action_function(action_data, project, live_state)
