import os
from typing import Type, List
from unittest import TestCase

from moto import mock_aws
from moto.core.models import MockAWS
from pynamodb.models import Model


class PynamoTest(object):
    mock_aws: MockAWS = mock_aws()
    models: List[Type[Model]] = []
    _unset_region = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupCalled = False
        self.tearDownCalled = False

    @classmethod
    def _create_tables(cls):
        for model in cls.models:
            model.create_table(wait=True)

    @classmethod
    def _delete_tables(cls):
        for model in cls.models:
            model.delete_table()

    @classmethod
    def setUpClass(cls):
        if os.environ.get("AWS_DEFAULT_REGION") is None:
            cls._unset_region = True
            os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        cls.mock_aws.start()

    @classmethod
    def tearDownClass(cls):
        if cls._unset_region:
            del os.environ["AWS_DEFAULT_REGION"]
        cls.mock_aws.stop()

    def setUp(self):
        if not self.setupCalled:
            self.setupCalled = True
            self._create_tables()

    def tearDown(self):
        if not self.tearDownCalled:
            self.tearDownCalled = True
            self._delete_tables()
