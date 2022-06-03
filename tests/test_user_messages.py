#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest.mock import Mock

from ees_microsoft_teams.configuration import Configuration
from ees_microsoft_teams.microsoft_teams_user_messages import \
    MSTeamsUserMessage

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=CONFIG_FILE
    )

    logger = logging.getLogger("unit_test_user_messages")
    return configuration, logger


def create_user_message_obj():
    """This function create user chat object for test.
    """
    configs, logger = settings()
    return MSTeamsUserMessage('token', {}, logger, configs)

@pytest.mark.parametrize(
    "source_tabs, mock_tabs_document",
    [
        (
            [{
                'type': 'User Chat Tabs',
                'id': 'b92dd123-1624-425c-a808-2f11e03534a5',
                'title': 'Some random board',
                '_allow_permissions': ['123'],
                'url': 'https://trello.com/b/kS2FslqK/some-random-board'
            }],
            {
                "value": [
                    {
                        "id": "b92dd123-1624-425c-a808-2f11e03534a5",
                        "displayName": "Some random board",
                        "sortOrderIndex": "10000100100",
                        "messageId": "1607412162267",
                        "configuration": {
                            "websiteUrl": "https://trello.com/b/kS2FslqK/some-random-board",
                            "dateAdded": "2020-12-08T07:22:40.001Z"
                        },
                    }
                ]
            },
        )
    ],
)
def test_get_user_tabs(source_tabs, mock_tabs_document):
    """Test the method of fetching user tabs"""
    user_message_obj = create_user_message_obj()
    user_message_obj.client.get = Mock(return_value=mock_tabs_document)
    tabs_schema_fields = {'id': 'id', 'title': 'displayName'}
    user_message_obj.get_schema_fields = Mock(return_value=tabs_schema_fields)
    target_tabs = user_message_obj.fetch_tabs("123", [1, 2, 3], "2020-12-08T07:17:29.748Z", "2020-12-08T07:17:29.748Z")
    assert source_tabs == target_tabs
