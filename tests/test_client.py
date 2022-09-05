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


@pytest.mark.parametrize(
    "mock_channel_messages, source_channel_messages",
    [
        (
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#teams('team1')/channels('team1_channel1')/messages",
                "@odata.count": 16,
                "value": [
                    {
                        "id": "1661755405876",
                        "replyToId": None,
                        "etag": "1661755405876",
                        "messageType": "message",
                        "createdDateTime": "2022-08-29T06:43:25.876Z",
                        "lastModifiedDateTime": "2022-08-29T06:43:25.876Z",
                        "lastEditedDateTime": None,
                        "deletedDateTime": None,
                        "subject": None,
                        "summary": None,
                        "chatId": None,
                        "importance": "normal",
                        "locale": "en-us",
                        "webUrl": "https://teams.microsoft.com/l/message/19%3Ajy3xYhYibQjuEqyNebuqYuG48vGfhjigtMqzjoq7Kfs1%40thread.tacv2/1661755405876?groupId=feffa8d9-33b9-42ac-87d6-b6a512472e27&tenantId=5186e740-5d4d-452f-b9c1-c8131cdefbe9&createdTime=1661755405876&parentMessageId=1661755405876",
                        "policyViolation": None,
                        "eventDetail": None,
                        "from": {
                            "application": None,
                            "device": None,
                            "user": {
                                "id": "1cd554ab-469a-4d74-93c7-33a05ea12342",
                                "displayName": "moxarth rathod",
                                "userIdentityType": "aadUser"
                            }
                        },
                        "body": {
                            "contentType": "text",
                            "content": "New Message for testing"
                        },
                        "channelIdentity": {
                            "teamId": "feffa8d9-33b9-42ac-87d6-b6a512472e27",
                            "channelId": "19:jy3xYhYibQjuEqyNebuqYuG48vGfhjigtMqzjoq7Kfs1@thread.tacv2"
                        },
                        "attachments": [],
                        "mentions": [],
                        "reactions": []
                    },
                ]
            },
            [
                {
                        "id": "1661755405876",
                        "replyToId": None,
                        "etag": "1661755405876",
                        "messageType": "message",
                        "createdDateTime": "2022-08-29T06:43:25.876Z",
                        "lastModifiedDateTime": "2022-08-29T06:43:25.876Z",
                        "lastEditedDateTime": None,
                        "deletedDateTime": None,
                        "subject": None,
                        "summary": None,
                        "chatId": None,
                        "importance": "normal",
                        "locale": "en-us",
                        "webUrl": "https://teams.microsoft.com/l/message/19%3Ajy3xYhYibQjuEqyNebuqYuG48vGfhjigtMqzjoq7Kfs1%40thread.tacv2/1661755405876?groupId=feffa8d9-33b9-42ac-87d6-b6a512472e27&tenantId=5186e740-5d4d-452f-b9c1-c8131cdefbe9&createdTime=1661755405876&parentMessageId=1661755405876",
                        "policyViolation": None,
                        "eventDetail": None,
                        "from": {
                            "application": None,
                            "device": None,
                            "user": {
                                "id": "1cd554ab-469a-4d74-93c7-33a05ea12342",
                                "displayName": "moxarth rathod",
                                "userIdentityType": "aadUser"
                            }
                        },
                        "body": {
                            "contentType": "text",
                            "content": "New Message for testing"
                        },
                        "channelIdentity": {
                            "teamId": "feffa8d9-33b9-42ac-87d6-b6a512472e27",
                            "channelId": "19:jy3xYhYibQjuEqyNebuqYuG48vGfhjigtMqzjoq7Kfs1@thread.tacv2"
                        },
                        "attachments": [],
                        "mentions": [],
                        "reactions": []
                    },
            ]
        )
    ],
)
def test_get_channel_messages(mock_channel_messages, source_channel_messages, requests_mock):
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
        "https://graph.microsoft.com/v1.0/teams/team1/channels/team1_channel1/messages",
        headers=headers,
        json=mock_channel_messages,
        status_code=200,
    )

    # Execute
    target_channel_messages = client_obj.get_channel_messages(
        next_url="https://graph.microsoft.com/v1.0/teams/team1/channels/team1_channel1/messages",
        start_time="2022-08-28T06:43:25.876Z",
        end_time="2022-08-30T06:43:25.876Z",
        channel_name="team1_channel1"
    )

    # Assert
    assert source_channel_messages == target_channel_messages


@pytest.mark.parametrize(
    "mock_calendars, source_calendars",
    [
        (
            {
                "value": [
                    {
                        "@odata.etag": "W/\"ROgxdw/e70aHEaCwahab/wAAknJgrg==\"",
                        "id": "AAMkAGYzODA4NGZmLTVlYmMtNDAwZS05YjA4LWUyNWEyMzM2MTU5YQBGAAAAAAA9zJOrVoPyQqp-hU5eRwlNBwBE6DF3D97vRocRoLBqFpv-AAAAAAENAABE6DF3D97vRocRoLBqFpv-AACSo-IiAAA=",
                        "createdDateTime": "2022-08-29T06:45:18.9050143Z",
                        "lastModifiedDateTime": "2022-08-29T06:47:19.5235027Z",
                        "hasAttachments": False,
                        "subject": "New Scrum Meeting",
                        "bodyPreview": "",
                        "isAllDay": False,
                        "isCancelled": False,
                        "isOrganizer": True,
                        "type": "singleInstance",
                        "webLink": "https://outlook.office365.com/owa/?itemid=AAMkAGYzODA4NGZmLTVlYmMtNDAwZS05YjA4LWUyNWEyMzM2MTU5YQBGAAAAAAA9zJOrVoPyQqp%2FhU5eRwlNBwBE6DF3D97vRocRoLBqFpv%2FAAAAAAENAABE6DF3D97vRocRoLBqFpv%2FAACSo%2FIiAAA%3D&exvsurl=1&path=/calendar/item",
                        "recurrence": None,
                        "onlineMeeting": None,
                        "body": {
                            "contentType": "html",
                            "content": ""
                        },
                        "start": {
                            "dateTime": "2022-08-30T08:30:00.0000000",
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": "2022-08-30T09:00:00.0000000",
                            "timeZone": "UTC"
                        },
                        "attendees": [],
                        "organizer": {
                            "emailAddress": {
                                "name": "Alex Wilber",
                                "address": "Alex@12345.onmicrosoft.com"
                            }
                        }
                    }
                ]
            },
            [
                    {
                        "@odata.etag": "W/\"ROgxdw/e70aHEaCwahab/wAAknJgrg==\"",
                        "id": "AAMkAGYzODA4NGZmLTVlYmMtNDAwZS05YjA4LWUyNWEyMzM2MTU5YQBGAAAAAAA9zJOrVoPyQqp-hU5eRwlNBwBE6DF3D97vRocRoLBqFpv-AAAAAAENAABE6DF3D97vRocRoLBqFpv-AACSo-IiAAA=",
                        "createdDateTime": "2022-08-29T06:45:18.9050143Z",
                        "lastModifiedDateTime": "2022-08-29T06:47:19.5235027Z",
                        "hasAttachments": False,
                        "subject": "New Scrum Meeting",
                        "bodyPreview": "",
                        "isAllDay": False,
                        "isCancelled": False,
                        "isOrganizer": True,
                        "type": "singleInstance",
                        "webLink": "https://outlook.office365.com/owa/?itemid=AAMkAGYzODA4NGZmLTVlYmMtNDAwZS05YjA4LWUyNWEyMzM2MTU5YQBGAAAAAAA9zJOrVoPyQqp%2FhU5eRwlNBwBE6DF3D97vRocRoLBqFpv%2FAAAAAAENAABE6DF3D97vRocRoLBqFpv%2FAACSo%2FIiAAA%3D&exvsurl=1&path=/calendar/item",
                        "recurrence": None,
                        "onlineMeeting": None,
                        "body": {
                            "contentType": "html",
                            "content": ""
                        },
                        "start": {
                            "dateTime": "2022-08-30T08:30:00.0000000",
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": "2022-08-30T09:00:00.0000000",
                            "timeZone": "UTC"
                        },
                        "attendees": [],
                        "organizer": {
                            "emailAddress": {
                                "name": "Alex Wilber",
                                "address": "Alex@12345.onmicrosoft.com"
                            }
                        }
                    }
                ]
        )
    ],
)
def test_get_calendars(mock_calendars, source_calendars, requests_mock):
    """ test get_calendars method of client file
    """
    # Setup
    _, _ = settings()
    client_obj = create_client_obj()
    headers = {
        "authorization": "Bearer dummy_access_token",
        "content-type": "application/json",
    }
    requests_mock.get(
        "https://graph.microsoft.com/v1.0/users/1/events",
        headers=headers,
        json=mock_calendars,
        status_code=200,
    )

    # Execute
    target_calendars = client_obj.get_calendars(
        next_url="https://graph.microsoft.com/v1.0/users/1/events",
        start_time="2022-08-28T06:47:19.5235027Z",
        end_time="2022-08-30T06:47:19.5235027Z",
    )

    # Assert
    assert source_calendars == target_calendars
