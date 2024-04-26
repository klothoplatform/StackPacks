import json
import logging
import os
import sys
from enum import Enum
from typing import Dict

app_log_file = os.getenv("APP_LOG_FILE", None)

# Create a custom logger
logger = logging.getLogger(__name__)

# Create handlers and formatters
c_handler = logging.StreamHandler(sys.stdout)
file_handler = None

c_format = logging.Formatter(
    "%(name)s - %(pathname)s:%(lineno)d - %(levelname)s - %(asctime)s - %(message)s"
)
c_handler.setFormatter(c_format)

log_handlers = [c_handler]
if app_log_file is not None:
    file_handler = logging.FileHandler(app_log_file)
    file_handler.setFormatter(c_format)
    log_handlers.append(file_handler)

# Add handlers to the logger
logger.handlers = log_handlers
logger.setLevel(logging.DEBUG)


class MetricNames(Enum):
    ENGINE_FAILURE = "EngineFailure"
    IAC_GENERATION_FAILURE = "IacGenerationFailure"
    READ_LIVE_STATE_FAILURE = "ReadLiveStateFailure"
    DEPLOYMENT_WORKFLOW_FAILURE = "DeploymentWorkflowFailure"
    DESTROY_WORKFLOW_FAILURE = "DestroyWorkflowFailure"
    PULUMI_DEPLOYMENT_FAILURE = "DeploymentFailure"
    PULUMI_TEAR_DOWN_FAILURE = "TeardownFailure"
    PRE_DEPLOY_ACTIONS_FAILURE = "PreDeployActionsFailure"


class MetricDimensions(Enum):
    PROJECT_ID = "ProjectId"
    APP_ID = "AppId"


class MetricsLogger:
    def __init__(self, project_id: str, app_id: str):
        self.project_id = project_id
        self.app_id = app_id
        self.dimensions = {
            MetricDimensions.PROJECT_ID.value: project_id,
            MetricDimensions.APP_ID.value: app_id,
        }
        pass

    def log_metric(
        self, metric_name: MetricNames, value: int, dimensions: Dict[str, str] = None
    ):
        """
        Logs a metric to stdout.
        :param metric_name: The name of the metric.
        :param value: The value of the metric.
        :param dimensions: A dictionary of dimensions for the metric (optional).
        """
        metric_data = {"metric": metric_name.value, "value": value}
        metric_data.update(self.dimensions)
        if dimensions:
            metric_data.update(dimensions)
        print(json.dumps(metric_data))
