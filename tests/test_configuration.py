#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_microsoft_teams.configuration import Configuration  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def create_configuration_obj():
    """This function create Configuration object for test."""
    return Configuration(file_name=CONFIG_FILE)


def test_get_value():
    """This method tests the get_value function."""

    # Setup
    config_obj = create_configuration_obj()

    # Execute
    source_retry = config_obj.get_value('retry_count')

    # Assert
    assert source_retry == 3
