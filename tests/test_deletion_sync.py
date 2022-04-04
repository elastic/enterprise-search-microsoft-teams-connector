#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys

import pytest
from elastic_enterprise_search import WorkplaceSearch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest.mock import Mock

from ees_microsoft_teams.configuration import Configuration
from ees_microsoft_teams.deletion import Deletion

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it"""
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_deletion_sync")
    return configuration, logger


def create_deletion_obj():
    """This function create deletion object for test.
    """
    configs, logger = settings()
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    workplace_search_client = WorkplaceSearch(
        enterprise_search_host,
        http_auth=configs.get_value(
            "enterprise_search.api_key"
        ),
    )
    return Deletion("token", configs, workplace_search_client, logger)


@pytest.mark.parametrize(
    "deleted_ids",
    [
        (
            ["844424930334011", "543528180028451862"],
        )
    ],
)
def test_sync_deleted_files(deleted_ids):
    """Test that delete files from Enterprise Search."""
    deletion_obj = create_deletion_obj()
    deletion_obj.workplace_search_client.delete_documents = Mock(return_value=True)
    deletion_obj.delete_documents(deleted_ids)
    assert True
