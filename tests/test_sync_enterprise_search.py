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
from unittest.mock import Mock  # noqa

from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.sync_enterprise_search import SyncEnterpriseSearch  # noqa
from elastic_enterprise_search import WorkplaceSearch  # noqa

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
    """This function create indexer object for test.
    """
    configs, logger = settings()
    enterprise_search_host = configs.get_value("enterprise_search.host_url")
    workplace_search_client = WorkplaceSearch(
        enterprise_search_host,
        http_auth=configs.get_value(
            "enterprise_search.api_key"
        ),
    )
    return SyncEnterpriseSearch(configs, logger, workplace_search_client, "queue")


def test_get_records_by_types():
    """Test for grouping records by their type"""
    enterprise_obj = create_sync_enterprise_obj()
    document = [
        {
            "id": 0,
            "title": "demo",
            "body": "Not much. It is a made up thing.",
            "url": "https://teams.microsoft.com/demo.txt",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "user_chats",
        }
    ]
    target_records_type = enterprise_obj.get_records_by_types(document)
    assert target_records_type == {'user_chats': 1}


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
    """Test that indexing document to workplace search"""
    caplog.set_level("INFO")
    enterprise_obj = create_sync_enterprise_obj()
    enterprise_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )
    enterprise_obj.index_documents(source_documents)
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
    caplog.set_level(log_level)
    enterprise_obj = create_sync_enterprise_obj()
    enterprise_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )
    enterprise_obj.index_documents(source_documents)
    assert error_msg in caplog.text


def test_add_permission_to_workplace(caplog):
    """Test that add permission to Enterprise Search."""
    caplog.set_level("INFO")
    enterprise_obj = create_sync_enterprise_obj()
    enterprise_obj.workplace_search_client.add_user_permissions = Mock(
        return_value=True
    )
    mock = Mock()
    mock.enterprise_obj.workplace_add_permission([{"user": "user1", "roles": "permission1"}])
    mock.enterprise_obj.workplace_add_permission.assert_called()
