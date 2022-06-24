#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import argparse
import logging
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unittest.mock import Mock

from ees_microsoft_teams.base_command import BaseCommand
from ees_microsoft_teams.configuration import Configuration
from ees_microsoft_teams.sync_enterprise_search import SyncEnterpriseSearch

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)

USER_MAPPING = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "user_mapping.csv",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=CONFIG_FILE
    )

    logger = logging.getLogger("unit_test_indexing")
    return configuration, logger


def create_sync_enterprise_obj():
    """This function create Workplace Search object for test.
    """
    configs, logger = settings()
    args = argparse.Namespace()
    args.config_file = CONFIG_FILE
    base_cmd = BaseCommand(args)
    return SyncEnterpriseSearch(
        configs, logger, base_cmd.workplace_search_custom_client, "queue"
    )


def test_get_records_by_object_types():
    """Test for grouping records by object type"""
    # Setup
    enterprise_obj = create_sync_enterprise_obj()
    documents = [
        {
            "id": 0,
            "title": "demo",
            "body": "Not much. It is a made up thing.",
            "url": "https://teams.microsoft.com/demo.txt",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "User Chat Messages",
        },
        {
            "id": 1,
            "title": "demo1",
            "body": "Not much. It is a made up thing.",
            "url": "https://teams.microsoft.com/demo.txt",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "Channel Chat message",
        }
    ]

    # Execute
    target_records_type = enterprise_obj.get_records_by_types(documents)

    # Assert
    assert target_records_type == {'User Chat Messages': 1, 'Channel Chat message': 1}


@pytest.mark.parametrize(
    "source_documents, mock_documents",
    [
        (
            [
                {
                    "id": 0,
                    "title": "demo",
                    "body": "Not much. It is a made up thing.",
                    "url": "https://teams.microsoft.com/demo.txt",
                    "created_at": "2019-06-01T12:00:00+00:00",
                    "type": "user_chats",
                },
                {
                    "id": 1,
                    "title": "demo1",
                    "body": "Not much. It is a made up thing.",
                    "url": "https://teams.microsoft.com/demo1.txt",
                    "created_at": "2019-06-01T12:00:00+00:00",
                    "type": "user_chats",
                },
            ],
            {"results": [{"id": "0", "errors": []}, {"id": "1", "errors": []}]},
        )
    ],
)
def test_index_documents(source_documents, mock_documents, caplog):
    """Test that indexing documents to workplace search"""
    # Setup
    caplog.set_level("INFO")
    enterprise_obj = create_sync_enterprise_obj()
    enterprise_obj.workplace_search_custom_client.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )

    # Execute
    enterprise_obj.index_documents(source_documents)

    # Assert
    assert "Total 2 user_chats indexed out of 2." in caplog.text


@pytest.mark.parametrize(
    "source_documents, mock_documents, log_level, error_msg",
    [
        (
            [
                {
                    "id": 0,
                    "title": "demo",
                    "body": "Not much. It is a made up thing.",
                    "url": "https://teams.microsoft.com/demo.txt",
                    "created_at": "2019-06-01T12:00:00+00:00",
                    "type": "user_chats",
                }
            ],
            {"results": [{"id": 0, "errors": ["not indexed"]}]},
            "ERROR",
            "Error while indexing 0. Error: ['not indexed']",
        )
    ],
)
def test_index_document_when_error_occurs(
    source_documents, mock_documents, log_level, error_msg, caplog
):
    """Test that display proper error message if document not indexed."""
    # Setup
    caplog.set_level(log_level)
    enterprise_obj = create_sync_enterprise_obj()
    enterprise_obj.workplace_search_custom_client.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )

    # Execute
    enterprise_obj.index_documents(source_documents)

    # Assert
    assert error_msg in caplog.text


def test_add_permission_to_workplace(caplog):
    """Test that add permission to Enterprise Search."""
    # Setup
    caplog.set_level("INFO")
    enterprise_obj = create_sync_enterprise_obj()
    enterprise_obj.workplace_search_custom_client.workplace_search_client.add_user_permissions = Mock(
        return_value=True
    )
    mock = Mock()

    # Execute
    mock.enterprise_obj.workplace_add_permission([{"user": "user1", "roles": "permission1"}])

    # Assert
    mock.enterprise_obj.workplace_add_permission.assert_called()
