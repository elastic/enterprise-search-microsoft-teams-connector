#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import logging
import os
import sys
from unittest.mock import Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.permission_sync_command import \
    PermissionSyncCommand  # noqa
from elastic_enterprise_search import WorkplaceSearch  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_permission")
    return configuration, logger


def create_permission_sync_obj():
    """This function create permission object for test."""
    configs, logger = settings()
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    workplace_search_client = WorkplaceSearch(
        enterprise_search_host,
        http_auth=configs.get_value("enterprise_search.api_key"),
    )
    return PermissionSyncCommand(logger, configs, workplace_search_client)


def test_list_user_permissions():
    """Test method for removing all the permissions from workplace search"""
    permission_sync_obj = create_permission_sync_obj()

    mock_response = {
                        "results": [
                            {
                                "user": "Dummy",
                                "permissions": ["19"],
                            }
                        ],
                    }

    permission_sync_obj.workplace_search_client.list_permissions = Mock(
        return_value=mock_response
    )
    target_permission = permission_sync_obj.list_user_permissions()
    assert target_permission == {"Dummy": ["19"]}
