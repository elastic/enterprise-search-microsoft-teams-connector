#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import argparse
import logging
import os
import sys
from unittest.mock import Mock

from elastic_enterprise_search import __version__
from packaging import version

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.enterprise_search_wrapper import \
    EnterpriseSearchWrapper  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)

ENTERPRISE_V8 = version.parse("8.0")


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(file_name=CONFIG_FILE)

    logger = logging.getLogger("unit_test_enterprise_search_wrapper")
    return configuration, logger


def create_enterprise_search_wrapper_obj():
    """This function create enterprise wrapper object for test."""
    configs, logger = settings()
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    return EnterpriseSearchWrapper(logger, configs, args)


def test_create_content_source(caplog):
    """Test execute method in Bootstrap file creates a content source in the Workplace Search."""
    wrapper_obj = create_enterprise_search_wrapper_obj()
    caplog.set_level("INFO")
    mock_response = {"id": "1234"}
    wrapper_obj.workplace_search_client.create_content_source = Mock(
        return_value=mock_response
    )
    wrapper_obj.create_content_source("schema", "display", "name", "is_searchable")
    assert (
        "Created ContentSource with ID 1234." in caplog.text
    )
