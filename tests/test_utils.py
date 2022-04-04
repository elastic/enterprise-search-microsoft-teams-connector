#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import logging

import pytest
from ees_microsoft_teams import utils
from ees_microsoft_teams.configuration import Configuration


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=os.path.join(
            os.path.join(os.path.dirname(__file__), "config"),
            "microsoft_teams_connector.yml",
        )
    )

    logger = logging.getLogger("unit_test_utils")
    return configuration, logger


def test_extract_api_response():
    """Test the extract content from tika"""
    targeted_content = utils.extract_api_response("hello")
    assert targeted_content == '\n\n\n\n\n\n\n\nhello\n'


def test_url_encode():
    """Tests that encode URL"""
    url_to_encode = '''http://ascii.cl?parameter="Click on 'URL Decode'!"'''
    targeted_encoded_url = utils.url_encode(url_to_encode)
    source_encoded_url = (
        "http%3A%2F%2Fascii.cl%3Fparameter%3D%22Click%20on%20''URL%20Decode''%21%22"
    )
    assert source_encoded_url == targeted_encoded_url


def test_url_decode():
    """Tests that decode URL"""
    url_to_encode = "id%253D184ff84d27c3613d%26quality%3Dmedium"
    targeted_decoded_url = utils.url_decode(url_to_encode)
    source_decoded_url = (
        "id%3D184ff84d27c3613d&quality=medium"
    )
    assert source_decoded_url == targeted_decoded_url


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
def test_insert_document_into_doc_id_storage(ids_list, source_documents, parent_id):
    """Test method for inserting the ids into doc id"""
    targeted_documents = utils.insert_document_into_doc_id_storage(ids_list, "1645460238462", "User Chat Messages", parent_id, "")
    assert source_documents == targeted_documents


def test_split_list_into_buckets():
    """Test that divide large number of documents amongst the total buckets."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    total_bucket = 3
    source_list = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
    targeted_list = utils.split_list_into_buckets(documents, total_bucket)
    assert targeted_list == source_list


def test_split_date_range_into_chunks():
    """Test for split date into chunks"""
    targeted_date_range = utils.split_date_range_into_chunks("2021-03-29T00:00:00Z", "2021-03-30T00:00:00Z", 1)
    assert targeted_date_range == ('2021-03-30T00:00:00Z', ['2021-03-29T00:00:00Z', '2021-03-30T00:00:00Z'])


def test_html_to_text():
    """Test for converting html to text"""
    _, logger = settings()
    content = "<b>Section </b><br/>BeautifulSoup<ul><li>Example <b>1</b></li>"
    targeted_content = utils.html_to_text(logger, content)
    assert targeted_content == "Section BeautifulSoupExample 1"


@pytest.mark.parametrize(
    "document_name, objects, source_schema_fields",
    [
        (
            "user_chats",
            {'User Chats': 'user_chats'},
            {'id': 'id', 'last_updated': 'lastModifiedDateTime', 'created_at': 'createdDateTime'},
        )
    ],
)
def test_get_schema_fields(document_name, objects, source_schema_fields):
    """Test the fetching of schema fields"""
    targeted_schema_fields = utils.get_schema_fields(document_name, objects)
    assert source_schema_fields == targeted_schema_fields


def test_get_records_by_types():
    """Test for grouping records by their type"""
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
    targeted_records_type = utils.get_records_by_types(document)
    assert targeted_records_type == {'user_chats': 1}
