#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest.mock import Mock

import pytest
from ees_microsoft_teams.configuration import Configuration
from ees_microsoft_teams.microsoft_teams_channels import MSTeamsChannels
from requests.models import Response
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

    logger = logging.getLogger("unit_test_channels")
    return configuration, logger


def create_channel_obj():
    """This function create channel object for test.
    """
    configs, logger = settings()
    local_storage = LocalStorage(logger)
    return MSTeamsChannels('token', logger, configs, local_storage)


@pytest.mark.parametrize(
    "mock_teams, teams_schema_field, source_teams",
    [
        (
            {
                "value": [
                    {
                        "id": "45b7d2e7-b882-4a80-ba97-10b7a63b8fa4",
                        "createdDateTime": "2018-12-22T02:21:05Z",
                        "description": "Self help community for golf",
                        "displayName": "Golf Assist",
                        "mail": "golfassist@contoso.com",
                        "mailNickname": "golfassist",
                        "renewedDateTime": "2018-12-22T02:21:05Z",
                    },
                ]
            },
            {
                'id': 'id',
                'title': 'displayName',
                'body': 'description',
                'created_at': 'createdDateTime'
            },
            [{
                'type': 'Teams',
                'id': '45b7d2e7-b882-4a80-ba97-10b7a63b8fa4',
                'title': 'Golf Assist',
                'body': 'Self help community for golf',
                '_allow_permissions': ['45b7d2e7-b882-4a80-ba97-10b7a63b8fa4'],
                'created_at': '2018-12-22T02:21:05Z'
            }],
        )
    ],
)
def test_get_all_teams(mock_teams, teams_schema_field, source_teams):
    """Test get all teams"""
    # Setup
    channel_obj = create_channel_obj()
    channel_obj.get_schema_fields = Mock(return_value=teams_schema_field)
    channel_obj.client.get = Mock(return_value=mock_teams)

    # Execute
    target_teams = channel_obj.get_all_teams([1, 2])

    # Assert
    assert target_teams == source_teams


@pytest.mark.parametrize(
    "mock_teams",
    [
        (
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#groups",
                "value": [
                    {
                        "id": "45b7d2e7-b882-4a80-ba97-10b7a63b8fa4",
                        "deletedDateTime": None,
                        "createdDateTime": "2018-12-22T02:21:05Z",
                        "description": "Self help community for golf",
                        "displayName": "Golf Assist",
                        "expirationDateTime": None,
                        "groupTypes": [
                            "Unified"
                        ],
                        "isAssignableToRole": "null",
                        "mail": "golfassist@contoso.com",
                        "mailNickname": "golfassist",
                        "preferredDataLocation": "CAN",
                        "renewedDateTime": "2018-12-22T02:21:05Z",
                    },
                ]
            }
        )
    ],
)
def test_get_team_members(mock_teams):
    """Test get members of team"""
    # Setup
    team_member_obj = create_channel_obj()
    team_member_obj.client.get = Mock(return_value=mock_teams)

    # Execute
    target_teams = team_member_obj.get_team_members()

    # Assert
    assert target_teams == {'Golf Assist': ['45b7d2e7-b882-4a80-ba97-10b7a63b8fa4']}


@pytest.mark.parametrize(
    "mock_channels",
    [
        (
            {
                "value": [
                    {
                        "id": "1658749655787",
                        "replyToId": "1658486708423",
                        "etag": "1658749655787",
                        "messageType": "message",
                        "createdDateTime": "2022-07-25T11: 47: 35.787Z",
                        "lastModifiedDateTime": "2022-07-25T11: 47: 35.787Z",
                        "lastEditedDateTime": None,
                        "deletedDateTime": None,
                        "subject": None,
                        "summary": None,
                        "chatId": None,
                        "importance": "normal",
                        "locale": "en-us",
                        "webUrl": "https: //teams.microsoft.com/l/message/19%3A751b4b0aa2ac4fba9c21ea3c69af381a%40thread.tacv2/1658749655787?groupId=feffa8d9-33b9-42ac-87d6-b6a512472e27&tenantId=5186e740-5d4d-452f-b9c1-c8131cdefbe9&createdTime=1658749655787&parentMessageId=1658486708423",
                        "policyViolation": None,
                        "eventDetail": None,
                        "from": {
                            "application": None,
                            "device": None,
                            "user": {
                                "id": "1cd554ab-469a-4d74-93c7-33a05ea12342",
                                "displayName": "Joni Sherman",
                                "userIdentityType": "aadUser"
                            }
                        },
                        "body": {
                            "contentType": "text",
                            "content": "Hi everyone"
                        },
                        "channelIdentity": {
                            "teamId": "feffa8d9-33b9-42ac-87d6-b6a512472e27",
                            "channelId": "19:751b4b0aa2ac4fba9c21ea3c69af381a@thread.tacv2"
                        },
                        "attachments": [],
                        "mentions": [],
                        "reactions": []
                    }
                ]
            }
        )
    ],
)
def test_get_message_replies(mock_channels):
    """Test get replies for messages"""
    team_replies_obj = create_channel_obj()
    team_replies_obj.client.get_channel_messages = Mock(return_value=mock_channels)
    target_channel_message_reply = team_replies_obj.get_message_replies(
        1, 2, 3, "2021-03-29T03:56:13.26Z", "2021-03-30T03:56:12.26Z"
    )
    print(target_channel_message_reply)
    assert target_channel_message_reply == "Joni Sherman - Hi everyone"


@pytest.mark.parametrize(
    "mock_channel_messages, mock_channel_message_documents, source_channels",
    [
        (
            {
                "value": [
                    {
                        "id": "1616990171266",
                        "replyToId": "None",
                        "etag": "1656484019648",
                        "messageType": "unknownFutureValue",
                        "createdDateTime": "2021-03-29T03:56:11.266Z",
                        "lastModifiedDateTime": "2021-03-29T03:56:11.266Z",
                        "lastEditedDateTime": "None",
                        "deletedDateTime": "None",
                        "subject": "dummy",
                        "summary": "None",
                        "chatId": "None",
                        "importance": "normal",
                        "locale": "en-us",
                        "webUrl": "https://teams.microsoft.com/l/message/11616990171266&parentMessageId=1616990032035",
                        "from": "None",
                        "policyViolation": "None",
                        "body": {
                            "contentType": "text",
                            "content": "Robin Kline - Hello World\nReplies:\nRobin Kline - Hello World",
                        },
                        "channelIdentity": {
                            "teamId": "6269510a-24f6-422a-807c-2a1b3b29a2ff",
                            "channelId": "19:AHjix5AhJlpjjapFakpEbja0PGNlvPnjacGN-9EqzXs1@thread.tacv2",
                        },
                        "attachments": [],
                        "mentions": [],
                        "reactions": [],
                        "eventDetail": {
                            "@odata.type": "#microsoft.graph.channelAddedEventMessageDetail",
                            "channelId": "19:c11ff4abd0454db282f46cde24ad5848@thread.tacv2",
                            "channelDisplayName": "TestTeam-8_Channel-15",
                            "initiator": {
                                "application": "None",
                                "device": "None",
                                "user": {
                                    "id": "1cd554ab-469a-4d74-93c7-33a05ea12342",
                                    "displayName": "None",
                                    "userIdentityType": "aadUser",
                                },
                            },
                        },
                    }
                ]
            },
            [{
                "type": "Channel Messages",
                "title": "dummy",
                "body": "Robin Kline - Hello World\nReplies:\nRobin Kline - Hello World",
                "id": "1616990171266",
                "url": "https://teams.microsoft.com/l/message/11616990171266&parentMessageId=1616990032035",
                "last_updated": "2021-03-29T03:56:11.266Z",
                "created_at": "2021-03-29T03:56:11.266Z",
            }],
            [{
                "19:09fc54a3141a45d0": [{"title": "dummy", "id": 1, }],
            }]
        )
    ],
)
def test_get_channel_messages(mock_channel_messages, mock_channel_message_documents, source_channels):
    """Test get messages for channels"""
    team_channel_obj = create_channel_obj()
    team_channel_obj.client.get_channel_messages = Mock(
        return_value=mock_channel_messages
    )
    team_channel_obj.get_channel_messages_documents = Mock(return_value=mock_channel_message_documents)
    target_channel_messages = team_channel_obj.get_channel_messages(
        source_channels, [1, 2], "2021-03-29T03:56:11.26Z", "2021-03-30T03:56:11.2Z"
    )
    source_channel_message = [
        {
            "type": "Channel Messages",
            "title": "dummy",
            "body": "Robin Kline - Hello World\nReplies:\nRobin Kline - Hello World",
            "id": "1616990171266",
            "url": "https://teams.microsoft.com/l/message/11616990171266&parentMessageId=1616990032035",
            "last_updated": "2021-03-29T03:56:11.266Z",
            "created_at": "2021-03-29T03:56:11.266Z",
        }
    ]
    print(target_channel_messages)
    assert source_channel_message == target_channel_messages


@pytest.mark.parametrize(
    "channel_schema, source_teams, source_channels",
    [
        (
            {
                'id': 'id',
                'url': 'webUrl',
                'title': 'displayName',
                'body': 'description',
                'created_at': 'createdDateTime'
            },
            [{
                1: [{
                    'type': 'Channels',
                    'id': '1',
                    'url': 'https://teams.microsoft.com/l/',
                    'title': 'General',
                    'body': 'description',
                    '_allow_permissions': [1],
                    'created_at': '2017-07-31T18:56:16.533Z'
                }]
            }],
            [{
                'type': 'Channels',
                'id': '1',
                'url': 'https://teams.microsoft.com/l/',
                'title': 'General',
                '_allow_permissions': [1],
                'body': 'description',
                'created_at': '2017-07-31T18:56:16.533Z'
            }]
        )
    ],
)
def test_get_team_channels(channel_schema, source_teams, source_channels):
    """Test get channels for teams"""
    # Setup
    channel_tabs_obj = create_channel_obj()
    teams = [{"title": "dummy", "id": 1}]
    new_response = Response()
    new_response._content = b'{"value": [{"id": "1", "createdDateTime": "2017-07-31T18:56:16.533Z", "displayName": "General", "description": "description", "email": "", "webUrl": "https://teams.microsoft.com/l/", "membershipType": "standard"}]}'
    new_response.status_code = 200
    channel_tabs_obj.client.get = Mock(return_value=new_response.json())
    channel_tabs_obj.get_schema_fields = Mock(return_value=channel_schema)

    # Execute
    target_teams, target_channels = channel_tabs_obj.get_team_channels(teams, [1, 2])

    # Assert
    assert target_teams == source_teams
    assert target_channels == source_channels
