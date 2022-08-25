import logging
import os

import pytest
from ees_microsoft_teams.configuration import Configuration
from ees_microsoft_teams.microsoft_teams_client import MSTeamsClient

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting.
    :param requests_mock: fixture for requests.get calls.
    """
    configuration = Configuration(file_name=CONFIG_FILE)
    logger = logging.getLogger("unit_test_full_sync_command")
    return configuration, logger


def create_client_obj():
    """This function create client object for test.
    """
    configs, logger = settings()
    return MSTeamsClient(logger, 'token', configs)


@pytest.mark.parametrize(
    "mock_teams, source_teams",
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
            [
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
        )
    ],
)
def test_get_teams(mock_teams, source_teams, requests_mock):
    """ Test get_teams method of client file
    """
    # Setup
    _, _ = settings()
    client_obj = create_client_obj()
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://graph.microsoft.com/v1.0/groups?$top=999",
        headers=headers,
        json=mock_teams,
        status_code=200,
    )

    # Execute
    target_teams = client_obj.get_teams("https://graph.microsoft.com/v1.0/groups")

    # Assert
    assert source_teams == target_teams


@pytest.mark.parametrize(
    "mock_channels, source_channels",
    [
        (
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#teams('441b02e8-3dd8-4640-9d8b-bb0b6f2ce439')/channels",
                "@odata.count": 16,
                "value": [
                    {
                        "id": "19:45f123d269a94101bebb60b7678a45c2@thread.tacv2",
                        "createdDateTime": "2022-06-29T06:25:09.386Z",
                        "displayName": "Test Channel",
                        "description": "Channel for testing purpose",
                        "tenantId": "5186e740-5d4d-452f-b9c1-c8131cdefbe9",
                        "webUrl": "https://teams.microsoft.com/l/channel/19%3A45f123d269a94101bebb60b7678a45c2%40thread.tacv2/TestTeam-3_Channel-1?groupId=441b02e8-3dd8-4640-9d8b-bb0b6f2ce439&tenantId=5186e740-5d4d-452f-b9c1-c8131cdefbe9&allowXTenantAccess=False",
                        "membershipType": "standard"
                    },
                ]
            },
            [
                {
                    "id": "19:45f123d269a94101bebb60b7678a45c2@thread.tacv2",
                    "createdDateTime": "2022-06-29T06:25:09.386Z",
                    "displayName": "Test Channel",
                    "description": "Channel for testing purpose",
                    "tenantId": "5186e740-5d4d-452f-b9c1-c8131cdefbe9",
                    "webUrl": "https://teams.microsoft.com/l/channel/19%3A45f123d269a94101bebb60b7678a45c2%40thread.tacv2/TestTeam-3_Channel-1?groupId=441b02e8-3dd8-4640-9d8b-bb0b6f2ce439&tenantId=5186e740-5d4d-452f-b9c1-c8131cdefbe9&allowXTenantAccess=False",
                    "membershipType": "standard"
                },
            ]
        )
    ],
)
def test_get_channels(mock_channels, source_channels, requests_mock):
    """ test get_channels method of client file
    """
    # Setup
    _, _ = settings()
    client_obj = create_client_obj()
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://graph.microsoft.com/v1.0/teams/1/channels",
        headers=headers,
        json=mock_channels,
        status_code=200,
    )

    # Execute
    target_channels = client_obj.get_teams("https://graph.microsoft.com/v1.0/teams/1/channels")

    # Assert
    assert source_channels == target_channels
