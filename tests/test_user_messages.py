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
    "chats, source_meeting",
    [
        (
            {
                "id": "1615943825123",
                "createdDateTime": "2021-03-1706:47:05.123Z",
                "lastModifiedDateTime": "2021-03-1706:47:05.123Z",
                "chatId": "19:2da4c29f6d7041eca70b638b43d45437@thread.v2",
                "eventDetail": {
                    "@odata.type": "#microsoft.graph.callRecordingEventMessageDetail",
                    "callId": "String",
                    "callRecordingDisplayName": "String",
                    "callRecordingUrl": "https://.sharepoint.com/",
                    "callRecordingDuration": "String (duration)",
                    "callRecordingStatus": "String",
                }
            },
            {
                'type': 'Meeting Recording',
                'id': 'String',
                'title': 'String',
                '_allow_permissions': ['19:88f620c0269c1f28f48a20d1@thread.v2'],
                'url': 'https://.sharepoint.com/'
            }
        )
    ],
)
def test_fetch_meeting_recording(chats, source_meeting):
    """Test the fetching of meeting recordings."""
    user_message_obj = create_user_message_obj()
    target_meeting = user_message_obj.fetch_meeting_recording("19:88f620c0269c1f28f48a20d1@thread.v2", chats)
    assert source_meeting == target_meeting


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
    target_members, target_documents = user_message_obj.get_user_chats([1, 2, 3])
    assert source_documents == target_documents
    assert source_members == target_members


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
def test_get_user_chat_messages(user_chats_schema_value, chat_data, mock_chat_messages_document, source_documents):
    """Test the fetching of user messages for a chat"""
    user_message_obj = create_user_message_obj()
    user_message_obj.get_schema_fields = Mock(return_value=user_chats_schema_value)
    user_message_obj.client.get = Mock(return_value=mock_chat_messages_document)
    user_message_obj.fetch_tabs = Mock(return_value=[])
    target_documents = user_message_obj.get_user_chat_messages(
        [1, 2], {}, chat_data, '2020-12-08T23:53:05.801Z', '2020-12-08T23:53:05.801Z', 'token'
    )
    assert source_documents == target_documents
