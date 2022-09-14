#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import os
import sys
import json

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ees_microsoft_teams.local_storage import LocalStorage  # noqa

DIRECTORY_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "ees_microsoft_teams",
    "doc_ids"
)

DOC_ID_STORAGE_PATH = f"{DIRECTORY_PATH}/doc_ids.json"


def create_local_storage_obj():
    """This function create object of LocalStorage class for test"""
    logger = logging.getLogger("unit_test_local_storage")
    local_storage = LocalStorage(logger)
    return local_storage


def test_create_local_storage_directory():
    """This method test if directory is exits or not"""
    # Setup
    local_storage_obj = create_local_storage_obj()

    # Execute
    local_storage_obj.create_local_storage_directory()

    # Assert
    assert os.path.exists(DIRECTORY_PATH)


def test_get_storage_with_collection():
    """This method test get_storage_with_collection"""
    # Setup
    local_storage_obj = create_local_storage_obj()
    dummy_doc_ids_file = {
        "global_keys": [
            {
                "id": "abc123",
                "type": "channel messages",
                "parent id": "xyz123",
                "super_parent_id": "pqr123"
            }
        ],
        "delete_keys": []
    }
    with open(DOC_ID_STORAGE_PATH, "w") as outfile:
        json.dump(dummy_doc_ids_file, outfile, indent=4)
    local_storage_obj.ids_path_dict["teams"] = DOC_ID_STORAGE_PATH
    expected_response = {
        "global_keys": [
            {
                "id": "abc123",
                "type": "channel messages",
                "parent id": "xyz123",
                "super_parent_id": "pqr123"
            }
        ],
        "delete_keys": [
            {
                "id": "abc123",
                "type": "channel messages",
                "parent id": "xyz123",
                "super_parent_id": "pqr123"
            }
        ],
    }

    # Execute
    actual_response = local_storage_obj.get_documents_from_doc_id_storage("teams")
    print(actual_response)
    print('=======================')
    print(expected_response)

    # Assert
    assert expected_response == actual_response


@pytest.mark.parametrize(
    "ids_list, source_documents, parent_id",
    [
        (
            [{
                "id": "1645460238462",
                "type": "User Chat Messages",
                "parent_id": "19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2",
                "super_parent_id": ""
            }],
            [{
                "id": "1645460238462",
                "type": "User Chat Messages",
                "parent_id": "19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2",
                "super_parent_id": ""
            }],
            "19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2",
        )
    ],
)
def test_insert_document_into_doc_id_storage_when_no_new_id_added(ids_list, source_documents, parent_id):
    """Test method for inserting the ids into doc id"""
    local_storage_obj = create_local_storage_obj()
    target_documents = local_storage_obj.insert_document_into_doc_id_storage(
        ids_list, "1645460238462", "User Chat Messages", parent_id, ""
    )
    assert source_documents == target_documents


@pytest.mark.parametrize(
    "ids_list, source_documents, parent_id",
    [
        (
            [{
                "id": "1645460238462",
                "type": "User Chat Messages",
                "parent_id": "19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2",
                "super_parent_id": ""
            }],
            [{
                'id': '1645460238462',
                'type': 'User Chat Messages',
                'parent_id': '19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2',
                'super_parent_id': ''
            },
                {
                'id': '1645460238461',
                'type': 'User Chat Messages',
                'parent_id': '19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2',
                'super_parent_id': ''
            }
            ],
            "19:meeting_MDZlN2M4OTQtZWQ5Ny00MT@thread.v2",
        )
    ],
)
def test_insert_document_into_doc_id_storage_when_new_id_added(ids_list, source_documents, parent_id):
    """Test method for inserting the ids into doc id when new id is added to id list"""
    local_storage_obj = create_local_storage_obj()
    target_documents = local_storage_obj.insert_document_into_doc_id_storage(
        ids_list, "1645460238461", "User Chat Messages", parent_id, ""
    )
    assert source_documents == target_documents
