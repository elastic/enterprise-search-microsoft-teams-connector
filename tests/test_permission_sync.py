#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import argparse
import logging
import os
import sys
from unittest.mock import Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_microsoft_teams.base_command import BaseCommand
from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.permission_sync_command import \
    PermissionSyncCommand  # noqa
from elastic_enterprise_search import __version__
from packaging import version

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)
ENTERPRISE_V8 = version.parse("8.0")


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=CONFIG_FILE
    )

    logger = logging.getLogger("unit_test_permission")
    return configuration, logger


def create_permission_sync_obj():
    """This function create permission object for test.
    """
    configs, logger = settings()
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    base_cmd = BaseCommand(args)
    workplace_search_custom_client = base_cmd.workplace_search_custom_client
    return PermissionSyncCommand(logger, configs, workplace_search_custom_client)


def test_list_user_permissions():
    """Test that list all permissions from Workplace Search"""
    permission_sync_obj = create_permission_sync_obj()
    if version.parse(__version__) >= ENTERPRISE_V8:
        mock_response = {
            "results": [
                {
                    "content_source_id": "1234",
                    "external_user_id": "Dummy",
                    "external_user_properties": [
                        {
                            "attribute_name": "_elasticsearch_username",
                            "attribute_value": "Dummy",
                        }
                    ],
                    "permissions": ["19"],
                }
            ],
        }
        permission_sync_obj.workplace_search_custom_client.list_permissions = Mock(
            return_value=mock_response
        )

    else:
        mock_response = {
            "results": [
                {
                    "user": "Dummy",
                    "permissions": ["19"],
                }
            ],
        }
        permission_sync_obj.workplace_search_custom_client.list_permissions = Mock(
            return_value=mock_response
        )
    target_permission = permission_sync_obj.list_user_permissions()
    assert target_permission == {"Dummy": ["19"]}
