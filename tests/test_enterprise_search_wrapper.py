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

import pytest
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
def test_index_documents(source_documents, mock_documents):
    """Test that indexing documents to workplace search"""
    # Setup
    wrapper_obj = create_enterprise_search_wrapper_obj()
    wrapper_obj.workplace_search_client.index_documents = Mock(
        return_value=mock_documents
    )

    # Execute
    result = wrapper_obj.index_documents(source_documents, 1000)

    # Assert
    assert len(result["results"]) == len(source_documents)


@pytest.mark.parametrize(
    "deleted_ids",
    [(["844424930334011", "543528180028451862"],)],
)
def test_sync_deleted_documents(deleted_ids):
    """Test that documents deleted from Workplace Search."""
    # Setup
    wrapper_obj = create_enterprise_search_wrapper_obj()
    wrapper_obj.workplace_search_client.delete_documents = Mock(return_value=True)

    # Execute and Assert
    wrapper_obj.delete_documents(deleted_ids)
    wrapper_obj.workplace_search_client.delete_documents.assert_called()


def test_create_content_source(caplog):
    """Test execute method in Bootstrap file creates a content source in the Workplace Search."""
    # Setup
    wrapper_obj = create_enterprise_search_wrapper_obj()
    caplog.set_level("INFO")
    mock_response = {"id": "1234"}
    wrapper_obj.workplace_search_client.create_content_source = Mock(
        return_value=mock_response
    )

    # Execute
    wrapper_obj.create_content_source("schema", "display", "name", "is_searchable")

    # Assert
    assert (
        "Created ContentSource with ID 1234." in caplog.text
    )


def test_list_permissions():
    """Test that list all the permissions from Workplace Search."""
    wrapper_obj = create_enterprise_search_wrapper_obj()
    if version.parse(__version__) >= ENTERPRISE_V8:
        mock_response = {
            "meta": {
                "page": {"current": 1, "total_pages": 1, "total_results": 1, "size": 25}
            },
            "results": [
                {
                    "content_source_id": "1234",
                    "external_user_id": "Dummy",
                    "external_user_properties": [
                        {
                            "attribute_name": "_elasticsearch_username",
                            "attribute_value": "Dummy",
                        }
                    ],
                    "permissions": ["19"],
                }
            ],
        }
        wrapper_obj.workplace_search_client.list_external_identities = Mock(
            return_value=mock_response
        )

    else:
        mock_response = [
            {"user": "example.user", "permissions": ["permission1", "permission2"]}
        ]
        wrapper_obj.workplace_search_client.list_permissions = Mock(
            return_value=mock_response
        )
    target_list = wrapper_obj.list_permissions()
    assert target_list == mock_response


def test_remove_permissions(caplog):
    """Test that remove the permission in Workplace Search."""
    caplog.set_level("INFO")
    wrapper_obj = create_enterprise_search_wrapper_obj()
    if version.parse(__version__) >= ENTERPRISE_V8:
        permissions = {
            "content_source_id": "1234",
            "external_user_id": "Dummy",
            "external_user_properties": [
                {
                    "attribute_name": "_elasticsearch_username",
                    "attribute_value": "Dummy",
                }
            ],
            "permissions": ["19"],
        }
    else:
        permissions = {"user": "Dummy", "permissions": ["19"]}
    if version.parse(__version__) >= ENTERPRISE_V8:
        wrapper_obj.workplace_search_client.delete_external_identity = Mock(
            return_value=True
        )
    else:

        wrapper_obj.workplace_search_client.remove_user_permissions = Mock(
            return_value=True
        )
    wrapper_obj.remove_permissions(permissions)
    assert "Successfully removed the permissions from the Workplace Search." in caplog.text


def test_add_permissions(caplog):
    """Test that add permissions in Workplace Search."""
    caplog.set_level("INFO")
    wrapper_obj = create_enterprise_search_wrapper_obj()
    user_name = "Dummy"
    permission_list = ["19"]
    if version.parse(__version__) >= ENTERPRISE_V8:
        wrapper_obj.workplace_search_client.create_external_identity = Mock()
        wrapper_obj.workplace_search_client.put_external_identity = Mock(
            return_value=True
        )
    else:
        wrapper_obj.workplace_search_client.add_user_permissions = Mock(
            return_value=True
        )
    wrapper_obj.add_permissions(user_name, permission_list)
    assert (
        f"Successfully indexed the permissions for {user_name} user into the Workplace Search"
        in caplog.text
    )
