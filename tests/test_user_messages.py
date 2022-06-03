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
