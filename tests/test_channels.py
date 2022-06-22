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
    new_response._content = b'{"value": [{"id": "1", "createdDateTime": "2017-07-31T18:56:16.533Z", "displayName": "General", "description": "description", "email": "", "webUrl": "https://teams.microsoft.com/l/", "membershipType": "standard"}]}'
    new_response.status_code = 200
    channel_tabs_obj.client.get = Mock(return_value=new_response)
    channel_tabs_obj.get_schema_fields = Mock(return_value=channel_schema)
    target_teams, target_channels = channel_tabs_obj.get_team_channels(teams, [1, 2])
    assert target_teams == source_teams
    assert target_channels == source_channels
