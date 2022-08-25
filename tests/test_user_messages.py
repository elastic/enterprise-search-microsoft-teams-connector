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
from ees_microsoft_teams.local_storage import LocalStorage

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
    local_storage = LocalStorage(logger)
    return MSTeamsUserMessage('token', logger, configs, local_storage)


@pytest.mark.parametrize(
    "mock_chats_document, source_documents, source_members",
    [
        (
            [
                {
                    "id": "19:meeting_MjdhNjM4YzUtYzExZi00OTFkLTkzZTAtNTVlNmZmMDhkNGU2@thread.v2",
                    "topic": "Meeting chat sample",
                    "createdDateTime": "2020-12-08T23:53:05.801Z",
                    "lastUpdatedDateTime": "2020-12-08T23:58:32.511Z",
                    "chatType": "meeting",
                    "members": [
                        {
                            "@odata.type": "#microsoft.graph.aadUserConversationMember",
                            "id": "123=",
                            "roles": [],
                            "displayName": "Tony Stark",
                            "userId": "4595d2f2-7b31-446c-84fd-9b795e63114b",
                            "email": "starkt@teamsgraph.onmicrosoft.com"
                        }
                    ]
                }
            ],
            [{
                'id': '19:meeting_MjdhNjM4YzUtYzExZi00OTFkLTkzZTAtNTVlNmZmMDhkNGU2@thread.v2',
                'topic': 'Meeting chat sample',
                'createdDateTime': '2020-12-08T23:53:05.801Z',
                'lastUpdatedDateTime': '2020-12-08T23:58:32.511Z',
                'chatType': 'meeting',
                'members': [{
                    '@odata.type': '#microsoft.graph.aadUserConversationMember',
                    'id': '123=',
                    'roles': [],
                    'displayName': 'Tony Stark',
                    'userId': '4595d2f2-7b31-446c-84fd-9b795e63114b',
                    'email': 'starkt@teamsgraph.onmicrosoft.com'
                }]
            }],
            {'Tony Stark': ['19:meeting_MjdhNjM4YzUtYzExZi00OTFkLTkzZTAtNTVlNmZmMDhkNGU2@thread.v2']},
        )
    ],
)
def test_get_user_chats(mock_chats_document, source_documents, source_members):
    """Test the method of fetching user chats"""
    user_message_obj = create_user_message_obj()
    user_message_obj.client.get_user_chats = Mock(return_value=mock_chats_document)
    target_members, target_documents = user_message_obj.get_user_chats([1, 2, 3])
    assert source_documents == target_documents
    assert source_members == target_members
