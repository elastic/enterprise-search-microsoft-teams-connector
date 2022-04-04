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
from ees_microsoft_teams.indexer import Indexer
from elastic_enterprise_search import WorkplaceSearch

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


def create_indexer_obj():
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
    return Indexer("token", workplace_search_client, "incremental", configs, logger, "checkpoint")


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
def test_bulk_index_documents(source_documents, mock_documents, caplog):
    """Test that indexing document to workplace search"""
    caplog.set_level("INFO")
    indexer_obj = create_indexer_obj()
    indexer_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )
    indexer_obj.bulk_index_documents(source_documents)
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
    indexer_obj = create_indexer_obj()
    indexer_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )
    indexer_obj.bulk_index_documents(source_documents)
    assert error_msg in caplog.text


def test_add_permission_to_workplace(caplog):
    """Test that add permission to Enterprise Search."""
    caplog.set_level("INFO")
    indexer_obj = create_indexer_obj()
    indexer_obj.workplace_search_client.add_user_permissions = Mock(
        return_value=True
    )
    mock = Mock()
    mock.indexer_obj.workplace_add_permission("user1", "permission1")
    mock.indexer_obj.workplace_add_permission.assert_called()


def test_index_permissions():
    """Test the index permissions"""
    indexer_obj = create_indexer_obj()
    indexer_obj.workplace_add_permission = Mock()
    with open(USER_MAPPING, "w") as outfile:
        outfile.write("dummy_user,user1")
        outfile.close()
    indexer_obj.index_permissions("dummy_user", "permission1")
    assert True
