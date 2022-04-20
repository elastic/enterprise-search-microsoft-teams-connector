#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import re  # noqa
from unittest.mock import Mock, patch  # noqa

import pytest  # noqa
from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.microsoft_teams_channels import MSTeamsChannels  # noqa
from requests.models import Response  # noqa

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
    return MSTeamsChannels('token', {}, logger, configs)


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
    channel_obj = create_channel_obj()
    channel_obj.get_schema_fields = Mock(return_value=teams_schema_field)
    channel_obj.client.get = Mock(return_value=mock_teams)
    target_teams = channel_obj.get_all_teams([1, 2])
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
    team_member_obj = create_channel_obj()
    team_member_obj.client.get = Mock(return_value=mock_teams)
    target_teams = team_member_obj.get_team_members()
    assert target_teams == {'Golf Assist': ['45b7d2e7-b882-4a80-ba97-10b7a63b8fa4']}


@pytest.mark.parametrize(
    "mock_channels",
    [
        (
            {
                "value": [
                    {
                        "id": "1501527482612",
                        "replyToId": "1501527481624",
                        "messageType": "message",
                        "createdDateTime": "2017-07-31T18:58:02.612Z",
                        "lastModifiedDateTime": "2017-07-31T18:58:02.612Z",
                        "subject": None,
                        "summary": None,
                        "chatId": None,
                        "eventDetail": None,
                        "from": {
                            "application": None,
                            "user": {
                                "id": "8b209ac8-08ff-4ef1-896d-3b9fde0bbf04",
                                "displayName": "Joni Sherman",
                                "userIdentityType": "aadUser"
                            }
                        },
                        "body": {
                            "contentType": "html",
                            "content": "<div>Hi everyone</div>"
                        },
                        "channelIdentity": {
                            "teamId": "02bd9fd6-8f93-4758-87c3-1fb73740a315",
                            "channelId": "19:d0bba23c2fc8413991125a43a54cc30e@thread.skype"
                        },
                        "attachments": [],
                    }
                ]
            }
        )
    ],
)
def test_get_message_replies(mock_channels):
    """Test get replies for messages"""
    team_replies_obj = create_channel_obj()
    team_replies_obj.client.get = Mock(return_value=mock_channels)
    target_channel_message_reply = team_replies_obj.get_message_replies(
        1, 2, 3, "2021-03-29T03:56:13.26Z", "2021-03-30T03:56:12.26Z"
        )
    assert target_channel_message_reply == "Joni Sherman - Hi everyone"


@pytest.mark.parametrize(
    "mock_channel_messages, channel_schema_field, source_channels",
    [
        (
            {
                "value": [
                    {
                        "id": "1616990171266",
                        "replyToId": "1616990032035",
                        "messageType": "message",
                        "createdDateTime": "2021-03-29T03:56:11.266Z",
                        "lastModifiedDateTime": "2021-03-29T03:56:11.266Z",
                        "deletedDateTime": None,
                        "subject": None,
                        "summary": None,
                        "chatId": None,
                        "webUrl": "https://teams.microsoft.com/l/message/11616990171266&parentMessageId=1616990032035",
                        "eventDetail": None,
                        "from": {
                            "application": None,
                            "device": None,
                            "user": {
                                       "id": "8ea0e38b-efb3-4757-924a-5f94061cf8c2",
                                       "displayName": "Robin Kline",
                                       "userIdentityType": "aadUser"
                            }
                        },
                        "body": {
                            "contentType": "text",
                            "content": "Hello World"
                        },
                        "channelIdentity": {
                            "teamId": "fbe2bf47-16c8-47cf-b4a5-4b9b187c508b",
                            "channelId": "19:4a95f7d8db4c4e7fae857bcebe0623e6@thread.tacv2"
                        },
                        "attachments": [],
                    }
                ]
            },
            {
                'id': 'id',
                'url': 'webUrl',
                'last_updated': 'lastModifiedDateTime',
                'created_at': 'createdDateTime'
            },
            [{
                "19:09fc54a3141a45d0": [{"title": "dummy", "id": 1, }],
            }]
        )
    ],
)
def test_get_channel_messages(mock_channel_messages, channel_schema_field, source_channels):
    """Test get messages for channels"""
    team_channel_obj = create_channel_obj()
    team_channel_obj.client.get = Mock(return_value=mock_channel_messages)
    team_channel_obj.get_schema_fields = Mock(return_value=channel_schema_field)
    target_channel_mesaages = team_channel_obj.get_channel_messages(
        source_channels, [1, 2], "2021-03-29T03:56:11.26Z", "2021-03-30T03:56:11.2Z"
    )
    source_channel_message = [{
        'type': 'Channel Messages',
        'title': 'dummy',
        'body': 'Robin Kline - Hello World\nReplies:\n',
        'id': '1616990171266',
        'url': 'https://teams.microsoft.com/l/message/11616990171266&parentMessageId=1616990032035',
        'last_updated': '2021-03-29T03:56:11.266Z',
        'created_at': '2021-03-29T03:56:11.266Z',
        '_allow_permissions': ['19:09fc54a3141a45d0']
        }]
    assert source_channel_message == target_channel_mesaages


@pytest.mark.parametrize(
    "mock_channel_tabs, source_channel_tabs, channel_tabs_schema, source_channels",
    [
        (
            {
                "value": [
                    {
                        "id": "b5d5f001-0471-49a5-aac4-04ef96683be0",
                        "displayName": "My Planner Tab",
                        "sortOrderIndex": "21",
                        "teamsApp": {
                            "id": "com.microsoft.teamspace.tab.planner",
                            "displayName": "Microsoft Planner",
                            "distributionMethod": "store"
                        },
                        "webUrl": "https://teams.microsoft.com/l/channel/19Tab"
                    }
                ]
            },
            [{
                'type': 'Channel Tabs',
                'id': 'b5d5f001-0471-49a5-aac4-04ef96683be0',
                'title': 'dummy-My Planner Tab',
                '_allow_permissions': ['19:09fc54a3141a45d0'],
                'url': 'https://teams.microsoft.com/l/channel/19Tab'
            }],
            {
                'id': 'id',
                'title': 'displayName',
                'url': 'webUrl'
            },
            [{
                "19:09fc54a3141a45d0": [{"title": "dummy", "id": 1, }],
            }]
        )
    ],
)
def test_get_channel_tabs(mock_channel_tabs, source_channel_tabs, channel_tabs_schema, source_channels):
    """Test get tabs for channels"""
    channel_tabs_obj = create_channel_obj()
    channel_tabs_obj.client.get = Mock(return_value=mock_channel_tabs)
    channel_tabs_obj.get_schema_fields = Mock(return_value=channel_tabs_schema)
    target_channel_tabs = channel_tabs_obj.get_channel_tabs(
        source_channels, [1, 2], "2021-03-29T03:56:11.266Z", "2021-03-30T03:56:11.266Z"
    )
    assert target_channel_tabs == source_channel_tabs


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
    channel_tabs_obj = create_channel_obj()
    teams = [{"title": "dummy", "id": 1}]
    new_response = Response()
    new_response._content = b'''{"value": [{"id": "1", "createdDateTime": "2017-07-31T18:56:16.533Z", "displayName":
    "General", "description": "description", "email": "", "webUrl": "https://teams.microsoft.com/l/", "membershipType":
    "standard"}]}'''
    new_response.status_code = 200
    channel_tabs_obj.client.get = Mock(return_value=new_response)
    channel_tabs_obj.get_schema_fields = Mock(return_value=channel_schema)
    target_teams, target_channels = channel_tabs_obj.get_team_channels(teams, [1, 2])
    assert target_teams == source_teams
    assert target_channels == source_channels
