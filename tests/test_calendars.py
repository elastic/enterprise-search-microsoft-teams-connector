#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest.mock import Mock  # noqa

import pytest  # noqa
from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.microsoft_teams_calendars import MSTeamsCalendar  # noqa
from ees_microsoft_teams.local_storage import LocalStorage  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=CONFIG_FILE
    )

    logger = logging.getLogger("unit_test_calendars")
    return configuration, logger


def create_calendar_obj():
    """This function create calendar object for test.
    """
    configs, logger = settings()
    local_storage = LocalStorage(logger)
    return MSTeamsCalendar('token', logger, configs, local_storage)


def test_calendars_for_cancelled_event():
    """Test for cancelled event in calendars"""
    calendar = create_calendar_obj()
    mock_users = [{
        'mail': 'Adams@M365x214355.onmicrosoft.com',
        'userId': '6e7b768e-07e2-4810-8459-485f84f8f204',
        'displayName': 'Conf Room Adams',
        'mailAddress': 'Adams@M365x214355.onmicrosoft.com'
    }]
    calendar.users_obj.get_all_users = Mock(return_value=mock_users)
    mock_calendar_response = [
        {
            "id": "AAMkAGIAAAoZDOFAAA=",
            "subject": "Orientation ",
            "isCancelled": True,
            "bodyPreview": "Dana, this is the time",
            "lastModifiedDateTime": "2017-04-21T10:00:00.0000000",
            "createdDateTime": "2017-04-21T10:00:00.0000000",
        }
    ]
    calendar.client.get_calendars = Mock(return_value=mock_calendar_response)
    source_permission, source_documents = calendar.get_calendars(
        [1, 2], "2017-04-21T10:00:00.0000000", "2020-12-05T23:10:36.925Z"
    )
    assert source_permission == {}
    assert source_documents == []


@pytest.mark.parametrize(
    "mock_users,mock_calendar_response",
    [
        (
            [{
                'mail': 'Adams@M365x214355.onmicrosoft.com',
                'userId': '6e7b768e-07e2-4810-8459-485f84f8f204',
                'displayName': 'Conf Room Adams',
                'mailAddress': 'Adams@M365x214355.onmicrosoft.com'
            }],
            [
                {
                    "id": "AQMkAGI5MWY5ZmUyLTJiNz",
                    "createdDateTime": "2017-07-31T18:57:51.0715544Z",
                    "lastModifiedDateTime": "2018-02-03T07:43:38.8913507Z",
                    "hasAttachments": False,
                    "subject": "Directors Meeting",
                    "bodyPreview": "description",
                    "sensitivity": "normal",
                    "isAllDay": False,
                    "isCancelled": False,
                    "showAs": "busy",
                    "type": "seriesMaster",
                    "onlineMeetingUrl": None,
                    "isOnlineMeeting": True,
                    "body": {
                        "contentType": "html",
                        "content": "<html><body><div>Join Microsoft Teams Online Meeting</div></body></html>"
                    },
                    "start": {
                        "dateTime": "2017-08-14T19:30:00.0000000",
                        "timeZone": "UTC"
                    },
                    "end": {
                        "dateTime": "2017-08-14T20:30:00.0000000",
                        "timeZone": "UTC"
                    },
                    "recurrence": {
                        "pattern": {
                            "type": "weekly",
                            "interval": 1,
                            "month": 0,
                            "dayOfMonth": 0,
                            "daysOfWeek": [
                                "monday",
                                "tuesday",
                                "thursday"
                            ],
                            "firstDayOfWeek": "sunday",
                            "index": "first"
                        },
                        "range": {
                            "type": "noEnd",
                            "startDate": "2017-08-14",
                            "endDate": "0001-01-01",
                            "recurrenceTimeZone": "Eastern Standard Time",
                            "numberOfOccurrences": 0
                        }
                    },
                    "attendees": [
                        {
                            "type": "required",
                            "status": {
                                "response": "accepted",
                                "time": "2017-07-31T18:57:55.2797039Z"
                            },
                            "emailAddress": {
                                "name": "Alex Wilber",
                                "address": "AlexW@M365x214355.onmicrosoft.com"
                            }
                        }
                    ],
                    "organizer": {
                        "emailAddress": {
                            "name": "HR Taskforce",
                            "address": "HRTaskforce@M365x214355.onmicrosoft.com"
                        }
                    },
                    "onlineMeeting": {
                        "joinUrl": "https://teams.microsoft.com/l/meet96be35"
                    },
                }
            ]
        )
    ],
)
def test_calendars_for_recurrence_event(mock_users, mock_calendar_response):
    """Test for weekly event in calendars"""
    calendar = create_calendar_obj()
    calendar.users_obj.get_all_users = Mock(return_value=mock_users)
    calendar.client.get_calendars = Mock(return_value=mock_calendar_response)
    source_permission, source_documents = calendar.get_calendars(
        [1, 2], "2017-04-21T10:00:00.0000000", "2020-12-05T23:10:36.925Z"
    )
    schedule = 'Recurrence: Occurs Every 1 week on monday,tuesday,thursday starting 2017-08-14 '
    attendees = 'Attendees: Alex Wilber(AlexW@M365x214355.onmicrosoft.com)'
    organizer = 'Organizer: HR Taskforce'
    description = 'Description: description'
    target_documents = [{
        'url': 'https://teams.microsoft.com/l/meet96be35',
        'type': 'Meeting',
        'id': 'AQMkAGI5MWY5ZmUyLTJiNz',
        'last_updated': '2018-02-03T07:43:38.8913507Z',
        'title': 'Directors Meeting',
        'created_at': '2017-07-31T18:57:51.0715544Z',
        'body': f'{schedule}\n{organizer} \n{attendees} \n{description}',
        '_allow_permissions': ['AQMkAGI5MWY5ZmUyLTJiNz']
    }]
    assert source_permission == {'Conf Room Adams': ['AQMkAGI5MWY5ZmUyLTJiNz']}
    assert source_documents == target_documents


@pytest.mark.parametrize(
    "mock_users, mock_calendar_response",
    [
        (
            [
                {
                    'mail': 'Adams@M365x214355.onmicrosoft.com',
                    'userId': '6e7b768e-07e2-4810-8459-485f84f8f204',
                    'displayName': 'Conf Room Adams',
                    'mailAddress': 'Adams@M365x214355.onmicrosoft.com'
                }
            ],
            [
                {
                    "id": "AQMkAGI5MWY5ZmUyLTJiNz",
                    "createdDateTime": "2017-07-31T18:57:51.0715544Z",
                    "lastModifiedDateTime": "2018-02-03T07:43:38.8913507Z",
                    "hasAttachments": False,
                    "subject": "Directors Meeting",
                    "bodyPreview": "description",
                    "sensitivity": "normal",
                    "isAllDay": False,
                    "isCancelled": False,
                    "showAs": "busy",
                    "type": "seriesMaster",
                    "webLink": "https://outlook.office365.com/calendar/deeplink/read/group/M365",
                    "onlineMeetingUrl": None,
                    "isOnlineMeeting": True,
                    "body": {
                        "contentType": "html",
                        "content": "<html><body><div>Join Microsoft Teams Online Meeting</div></body></html>"
                    },
                    "start": {
                        "dateTime": "2017-08-14T19:30:00.0000000",
                        "timeZone": "UTC"
                    },
                    "end": {
                        "dateTime": "2017-08-14T20:30:00.0000000",
                        "timeZone": "UTC"
                    },
                    "recurrence": {
                        "pattern": {
                            "type": "absoluteYearly",
                            "interval": 1,
                            "month": 0,
                            "dayOfMonth": 0,
                            "daysOfWeek": [
                                "monday",
                                "tuesday",
                                "thursday"
                            ],
                            "firstDayOfWeek": "sunday",
                            "index": "first"
                        },
                        "range": {
                            "type": "noEnd",
                            "startDate": "2017-08-14",
                            "endDate": "0001-01-01",
                            "recurrenceTimeZone": "Eastern Standard Time",
                            "numberOfOccurrences": 0
                        }
                    },
                    "attendees": [
                        {
                            "type": "required",
                            "status": {
                                "response": "accepted",
                                "time": "2017-07-31T18:57:55.2797039Z"
                            },
                            "emailAddress": {
                                "name": "Alex Wilber",
                                "address": "AlexW@M365x214355.onmicrosoft.com"
                            }
                        }
                    ],
                    "organizer": {
                        "emailAddress": {
                            "name": "HR Taskforce",
                            "address": "HRTaskforce@M365x214355.onmicrosoft.com"
                        }
                    },
                    "onlineMeeting": {
                        "joinUrl": "https://teams.microsoft.com/l/meet96be35"
                    },
                }
            ]
        )
    ],
)
def test_calendars_for_recurrence_event_yearly(mock_users, mock_calendar_response):
    """Test for yearly event in calendars"""
    calendar = create_calendar_obj()
    calendar.users_obj.get_all_users = Mock(return_value=mock_users)
    calendar.client.get_calendars = Mock(return_value=mock_calendar_response)
    source_permission, source_documents = calendar.get_calendars(
        [1, 2], "2017-04-21T10:00:00.0000000", "2020-12-05T23:10:36.925Z"
    )
    schedule = 'Recurrence: Occurs Every year on first monday,tuesday,thursday of  starting 2017-08-14 '
    attendees = 'Attendees: Alex Wilber(AlexW@M365x214355.onmicrosoft.com) '
    organizer = 'Organizer: HR Taskforce '
    description = 'Description: description'
    target_documents = [{
        'url': 'https://teams.microsoft.com/l/meet96be35',
        'type': 'Meeting',
                'id': 'AQMkAGI5MWY5ZmUyLTJiNz',
                'last_updated': '2018-02-03T07:43:38.8913507Z',
                'title': 'Directors Meeting',
                'created_at': '2017-07-31T18:57:51.0715544Z',
                '_allow_permissions': ['AQMkAGI5MWY5ZmUyLTJiNz'],
                'body': f'{schedule}\n{organizer}\n{attendees}\n{description}'
    }]
    assert source_permission == {'Conf Room Adams': ['AQMkAGI5MWY5ZmUyLTJiNz']}
    assert source_documents == target_documents


@pytest.mark.parametrize(
    "mock_users, mock_calendar_response",
    [
        (
            [{
                'mail': 'Adams@M365x214355.onmicrosoft.com',
                'userId': '6e7b768e-07e2-4810-8459-485f84f8f204',
                'displayName': 'Conf Room Adams',
                'mailAddress': 'Adams@M365x214355.onmicrosoft.com'
            }],
            [
                {
                    "id": "AQMkAGI5MWY5ZmUyLTJiNz",
                    "createdDateTime": "2017-07-31T18:57:51.0715544Z",
                    "lastModifiedDateTime": "2018-02-03T07:43:38.8913507Z",
                    "hasAttachments": False,
                    "subject": "Directors Meeting",
                    "bodyPreview": "description",
                    "sensitivity": "normal",
                    "isAllDay": False,
                    "isCancelled": False,
                    "showAs": "busy",
                    "type": "seriesMaster",
                    "webLink": "https://outlook.office365.com/calendar/deeplink/read/group/M365",
                    "onlineMeetingUrl": None,
                    "isOnlineMeeting": True,
                    "body": {
                        "contentType": "html",
                        "content": "<html><body><div>Join Microsoft Teams Online Meeting</div></body></html>"
                    },
                    "start": {
                        "dateTime": "2017-08-14T19:30:00.0000000",
                        "timeZone": "UTC"
                    },
                    "end": {
                        "dateTime": "2017-08-14T20:30:00.0000000",
                        "timeZone": "UTC"
                    },
                    "recurrence": {
                        "pattern": {
                            "type": "absoluteMonthly",
                            "interval": 1,
                            "month": 0,
                            "dayOfMonth": 0,
                            "daysOfWeek": [
                                "monday",
                                "tuesday"
                            ],
                            "firstDayOfWeek": "sunday",
                            "index": "first"
                        },
                        "range": {
                            "type": "noEnd",
                            "startDate": "2017-08-14",
                            "endDate": "0001-01-01",
                            "recurrenceTimeZone": "Eastern Standard Time",
                            "numberOfOccurrences": 0
                        }
                    },
                    "attendees": [
                        {
                            "type": "required",
                            "status": {
                                "response": "accepted",
                                "time": "2017-07-31T18:57:55.2797039Z"
                            },
                            "emailAddress": {
                                "name": "Alex Wilber",
                                "address": "AlexW@M365x214355.onmicrosoft.com"
                            }
                        }
                    ],
                    "organizer": {
                        "emailAddress": {
                            "name": "HR Taskforce",
                            "address": "HRTaskforce@M365x214355.onmicrosoft.com"
                        }
                    },
                    "onlineMeeting": {
                        "joinUrl": "https://teams.microsoft.com/l/meet96be35"
                    },
                }
            ]
        )
    ],
)
def test_calendars_for_recurrence_event_monthly(mock_users, mock_calendar_response):
    """Test for monthly event in calendars"""
    calendar = create_calendar_obj()
    calendar.users_obj.get_all_users = Mock(return_value=mock_users)
    calendar.client.get_calendars = Mock(return_value=mock_calendar_response)
    source_permission, source_documents = calendar.get_calendars(
        [1, 2], "2017-04-21T10:00:00.0000000", "2020-12-05T23:10:36.925Z"
    )
    schedule = 'Recurrence: Occurs Every 1 month on first monday,tuesday starting 2017-08-14 '
    attendees = 'Attendees: Alex Wilber(AlexW@M365x214355.onmicrosoft.com) '
    organizer = 'Organizer: HR Taskforce '
    description = 'Description: description'
    target_documents = [{
        'url': 'https://teams.microsoft.com/l/meet96be35',
        'type': 'Meeting',
                'id': 'AQMkAGI5MWY5ZmUyLTJiNz',
                'last_updated': '2018-02-03T07:43:38.8913507Z',
                'title': 'Directors Meeting',
                'created_at': '2017-07-31T18:57:51.0715544Z',
                '_allow_permissions': ['AQMkAGI5MWY5ZmUyLTJiNz'],
                'body': f'{schedule}\n{organizer}\n{attendees}\n{description}'
    }]
    assert source_permission == {'Conf Room Adams': ['AQMkAGI5MWY5ZmUyLTJiNz']}
    assert source_documents == target_documents


@pytest.mark.parametrize(
    "mock_users, mock_calendar_response",
    [
        (
            [{
                'mail': 'Adams@M365x214355.onmicrosoft.com',
                'userId': '6e7b768e-07e2-4810-8459-485f84f8f204',
                'displayName': 'Conf Room Adams',
                'mailAddress': 'Adams@M365x214355.onmicrosoft.com'
            }],
            [
                {
                    "@odata.etag": "W/\"ROgxdw/e70aHEaCwahab/wAAHieWMQ==\"",
                    "id": "123",
                    "createdDateTime": "2022-03-03T09:00:50.257586Z",
                    "lastModifiedDateTime": "2022-03-03T09:02:52.4379577Z",
                    "hasAttachments": False,
                    "subject": "Test meeting",
                    "bodyPreview": "Microsoft Teams",
                    "importance": "normal",
                    "isAllDay": False,
                    "isCancelled": False,
                    "isOrganizer": True,
                    "type": "singleInstance",
                            "onlineMeetingUrl": "null",
                            "isOnlineMeeting": True,
                            "onlineMeetingProvider": "teamsForBusiness",
                            "allowNewTimeProposals": True,
                            "recurrence": None,
                            "start": {
                                "dateTime": "2022-03-03T09:00:00.0000000",
                                "timeZone": "UTC"
                            },
                    "end": {
                                "dateTime": "2022-03-03T09:30:00.0000000",
                                "timeZone": "UTC"
                            },
                    "attendees": [
                                {
                                    "type": "required",
                                    "status": {
                                        "response": "none",
                                        "time": "0001-01-01T00:00:00Z"
                                    },
                                    "emailAddress": {
                                        "name": "Alex Wilber",
                                        "address": "AlexW@t8zsn.onmicrosoft.com"
                                    }
                                }
                            ],
                    "organizer": {
                                "emailAddress": {
                                    "name": "moxarth rathod",
                                    "address": "Moxarth@t8zsn.onmicrosoft.com"
                                }
                            },
                    "onlineMeeting": {
                                "joinUrl": "https://teams.microsoft.com/l/"
                            }
                }
            ]
        )
    ],
)
def test_calendars_for_recurrence_event_daily(mock_users, mock_calendar_response):
    """Test for daily event in calendars"""
    calendar = create_calendar_obj()
    calendar.users_obj.get_all_users = Mock(return_value=mock_users)
    calendar.client.get_calendars = Mock(return_value=mock_calendar_response)
    source_permission, source_documents = calendar.get_calendars(
        [1, 2], "2017-04-21T10:00:00.0000000", "2020-12-05T23:10:36.925Z"
    )
    schedule = 'Schedule: 03 Mar, 2022 at 09:00 to 03 Mar, 2022 at 09:30 '
    attendees = 'Attendees: Alex Wilber(AlexW@t8zsn.onmicrosoft.com) '
    organizer = 'Organizer: moxarth rathod '
    description = 'Description: Microsoft Teams'
    target_documents = [{
        'url': 'https://teams.microsoft.com/l/',
        'type': 'Meeting',
                'id': '123',
                'last_updated': '2022-03-03T09:02:52.4379577Z',
                'title': 'Test meeting',
                'created_at': '2022-03-03T09:00:50.257586Z',
                '_allow_permissions': ['123'],
                'body': f'{schedule}\n{organizer}\n{attendees}\n{description}'
    }]
    assert source_permission == {'Conf Room Adams': ['123']}
    assert source_documents == target_documents
