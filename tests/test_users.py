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
from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.microsoft_teams_users import MSTeamsUsers  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=CONFIG_FILE
    )

    logger = logging.getLogger("unit_test_users")
    return configuration, logger


def create_users_obj():
    """This function create user object for test.
    """
    configs, _ = settings()
    return MSTeamsUsers('token', configs)


@pytest.mark.parametrize(
    "request_return_value, source_users",
    [
        (
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                "value": [
                    {
                        "businessPhones": [],
                        "displayName": "Conf Room Adams",
                        "givenName": "null",
                        "jobTitle": "null",
                        "mail": "Adams@M365x214355.onmicrosoft.com",
                        "mobilePhone": "null",
                        "officeLocation": "null",
                        "preferredLanguage": "null",
                        "surname": "null",
                        "userPrincipalName": "Adams@M365x214355.onmicrosoft.com",
                        "id": "6e7b768e-07e2-4810-8459-485f84f8f204"
                    }
                ]
            },
            [{
                'mail': 'Adams@M365x214355.onmicrosoft.com',
                'userId': '6e7b768e-07e2-4810-8459-485f84f8f204',
                'displayName': 'Conf Room Adams',
                'mailAddress': 'Adams@M365x214355.onmicrosoft.com'
            }]
        )
    ],
)
def test_get_all_users(requests_mock, request_return_value, source_users):
    """Test for getting all users from Microsoft Teams"""
    user_obj = create_users_obj()
    request_header = {"Authorization": "Bearer token"}
    requests_mock.get(
        'https://graph.microsoft.com/v1.0/users', headers=request_header, json=request_return_value, status_code=200
    )
    target_users = user_obj.get_all_users()
    assert source_users == target_users
