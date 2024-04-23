import aiounittest

from src.deployer.models.workflow_job import WorkflowJob
from src.deployer.models.workflow_run import WorkflowRun
from src.project.models.app_deployment import AppDeployment
from src.project.models.project import Project
from tests.test_utils.pynamo_test import PynamoTest


class TestUtil(PynamoTest, aiounittest.AsyncTestCase):
    models = [AppDeployment, Project, WorkflowJob, WorkflowRun]
