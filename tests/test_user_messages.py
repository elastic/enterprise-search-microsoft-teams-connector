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
from unittest.mock import Mock, patch

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
    "mock_chats_document, source_documents, source_members",
    [
        (
            {
                "value": [
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
                ]
            },
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
    user_message_obj.client.get = Mock(return_value=mock_chats_document)
    targeted_members, targeted_documents = user_message_obj.get_user_chats([1, 2, 3])
    assert source_documents == targeted_documents
    assert source_members == targeted_members


@pytest.mark.parametrize(
    "user_chats_schema_value, chat_data, mock_chat_messages_document, source_documents",
    [
        (
            {
                "id": "id",
                "last_updated": "lastModifiedDateTime",
                "created_at": "createdDateTime",
            },
            [{
                'id': '19:meeting_MjdhNjM4YzUtYzExZi00OTFkLTkzZTAtNTVlNmZmMDhkNGU2@thread.v2',
                'topic': 'Meeting chat sample',
                'createdDateTime': '2020-12-08T23:53:05.801Z',
                'lastUpdatedDateTime': '2020-12-08T23:58:32.511Z',
                'chatType': 'meeting',
                "webUrl": "http://test.com",
                'members': [{
                    '@odata.type': '#microsoft.graph.aadUserConversationMember',
                    'id': '123=',
                    'roles': [],
                    'displayName': 'Tony Stark',
                    'userId': '4595d2f2-7b31-446c-84fd-9b795e63114b',
                    'email': 'starkt@teamsgraph.onmicrosoft.com'
                }]
            }],
            {
                "value": [
                    {
                        "id": "1616964509832",
                        "messageType": "message",
                        "createdDateTime": "2021-03-28T20:48:29.832Z",
                        "lastModifiedDateTime": "2021-03-28T20:48:29.832Z",
                        "deletedDateTime": None,
                        "subject": "hi",
                        "summary": "it is subject",
                        "chatId": "19:2da4c29f6d7041eca70b638b43d45437@thread.v2",
                        "eventDetail": None,
                        "from": {
                            "user": {
                                "id": "8ea0e38b-efb3-4757-924a-5f94061cf8c2",
                                "displayName": "Robin Kline",
                                "userIdentityType": "aadUser"
                            }
                        },
                        "body": {
                            "contentType": "text",
                            "content": "Hello world"
                        },
                        "attachments": [],
                        "mentions": [],
                        "reactions": []
                    },
                ]
            },
            [{
                'type': 'User Chat Messages',
                'id': '1616964509832',
                'last_updated': '2021-03-28T20:48:29.832Z',
                'created_at': '2021-03-28T20:48:29.832Z',
                'title': 'Meeting chat sample',
                'body': 'Robin Kline - Hello world',
                'url': 'http://test.com',
                '_allow_permissions': ['19:meeting_MjdhNjM4YzUtYzExZi00OTFkLTkzZTAtNTVlNmZmMDhkNGU2@thread.v2']
            }]
        )
    ],
)
@patch('ees_microsoft_teams.microsoft_teams_user_messages.MSALAccessToken')
def test_get_user_chat_messages(mocked, user_chats_schema_value, chat_data, mock_chat_messages_document, source_documents):
    """Test the fetching of user messages for a chat"""
    user_message_obj = create_user_message_obj()
    user_message_obj.get_schema_fields = Mock(return_value=user_chats_schema_value)
    user_message_obj.client.get = Mock(return_value=mock_chat_messages_document)
    targeted_documents = user_message_obj.get_user_chat_messages(
        [1, 2], {}, chat_data, '2020-12-08T23:53:05.801Z', '2020-12-08T23:53:05.801Z'
    )
    assert source_documents == targeted_documents
