#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import logging
import math
import os
import sys

import pytest
from ees_microsoft_teams import utils
from ees_microsoft_teams.configuration import Configuration

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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


def test_url_encode():
    """Tests that encode URL"""
    url_to_encode = '''http://ascii.cl?parameter="Click on 'URL Decode'!"'''
    target_encoded_url = utils.url_encode(url_to_encode)
    source_encoded_url = (
        "http%3A%2F%2Fascii.cl%3Fparameter%3D%22Click%20on%20''URL%20Decode''%21%22"
    )
    assert source_encoded_url == target_encoded_url


def test_url_decode():
    """Tests that decode URL"""
    url_to_encode = "id%253D184ff84d27c3613d%26quality%3Dmedium"
    target_decoded_url = utils.url_decode(url_to_encode)
    source_decoded_url = (
        "id%3D184ff84d27c3613d&quality=medium"
    )
    assert source_decoded_url == target_decoded_url


def test_split_list_into_buckets():
    """Test that divide large number of documents amongst the total buckets."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 10]
    total_bucket = 3
    target_list = utils.split_list_into_buckets(documents, total_bucket)
    count = 0
    for id_list in target_list:
        for id in id_list:
            if id in documents:
                count += 1
    assert len(documents) == count


def test_split_list_into_buckets_for_duplicate_values():
    """Test that divide large number of documents amongst the total buckets for duplicate values."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 4, 1, 3, 3, 2]
    total_bucket = 3
    target_list = utils.split_list_into_buckets(documents, total_bucket)
    count = 0
    for id_list in target_list:
        for id in id_list:
            if id in documents:
                count += 1
    assert len(documents) == count


def test_split_list_into_buckets_for_uneven_bucket():
    """Test that divide large number of documents amongst the total uneven buckets."""
    documents = [1, 2, 3, 4, 5, 6, 7, 8, 1, 4, 1]
    total_bucket = 3
    target_list = utils.split_list_into_buckets(documents, total_bucket)
    count = 0
    for id_list in target_list:
        for id in id_list:
            if id in documents:
                count += 1
    assert len(documents) == count


def test_split_date_range_into_chunks():
    """Test for split date into chunks"""
    target_date_range = utils.split_date_range_into_chunks("2021-03-29T00:00:00Z", "2021-03-30T00:00:00Z", 1)
    assert target_date_range == ('2021-03-30T00:00:00Z', ['2021-03-29T00:00:00Z', '2021-03-30T00:00:00Z'])


def test_html_to_text():
    """Test for converting html to text"""
    _, logger = settings()
    content = "<b>Section </b><br/>BeautifulSoup<ul><li>Example <b>1</b></li>"
    target_content = utils.html_to_text(logger, content)
    assert target_content == "Section BeautifulSoupExample 1"


@pytest.mark.parametrize(
    "document_name, object_type_to_index, source_schema_fields",
    [
        (
            "user_chats",
            {'User Chats': 'user_chats'},
            {'id': 'id', 'last_updated': 'lastModifiedDateTime', 'created_at': 'createdDateTime'},
        )
    ],
)
def test_get_schema_fields(document_name, object_type_to_index, source_schema_fields):
    """Test the fetching of schema fields"""
    target_schema_fields = utils.get_schema_fields(document_name, object_type_to_index)
    assert source_schema_fields == target_schema_fields


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
    target_records_type = utils.get_records_by_types(document)
    assert target_records_type == {'user_chats': 1}


def test_split_documents_into_equal_chunks():
    """Test the split of documents into equal chunk"""
    document = [
        {
            "id": 0,
            "title": "demo",
            "body": "Not much. It is a made up thing.",
            "url": "https://chats.microsoft.com/demo.txt",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "user_chats",
        },
        {
            "id": 1,
            "title": "teams_demo",
            "body": "This is a teams demo body.",
            "url": "https://teams.microsoft.com/demo.txt",
            "created_at": "2019-06-01T12:00:00+00:00",
            "type": "teams",
        }
    ]
    no_of_thread = 3
    source_chunk = math.ceil(len(document) / no_of_thread)
    target_chunk = utils.split_documents_into_equal_chunks(document, no_of_thread)
    assert len(target_chunk) == source_chunk


def test_split_documents_into_equal_bytes_with_lowest_possible_size():
    """Tests split functionality based on size"""
    # Setup
    document_to_split = [
        {"name": "dummy1", "body": "dummy1_body"},
        {"name": "dummy2", "body": "dummy2_body"},
        {"name": "dummy3", "body": "dummy3_body"},
        {"name": "dummy4", "body": "dummy4_body"},
        {"name": "dummy5", "body": "dummy5_body"},
        {"name": "dummy6", "body": "dummy6_body"},
    ]
    allowed_size = 1
    expected_output = [
        [{"name": "dummy1", "body": None}],
        [{"name": "dummy2", "body": None}],
        [{"name": "dummy3", "body": None}],
        [{"name": "dummy4", "body": None}],
        [{"name": "dummy5", "body": None}],
        [{"name": "dummy6", "body": None}],
    ]

    # Execute
    returned_document = utils.split_documents_into_equal_bytes(document_to_split, allowed_size)

    # Assert
    assert returned_document == expected_output


def test_split_documents_into_equal_bytes_with_optimum_size():
    """Tests split functionality based on size"""
    # Setup
    document_to_split = [
        {"name": "dummy1", "body": "dummy1_body"},
        {"name": "dummy2", "body": "dummy2_body"},
        {"name": "dummy3", "body": "dummy3_body"},
        {"name": "dummy4", "body": "dummy4_body"},
        {"name": "dummy5", "body": "dummy5_body"},
        {"name": "dummy6", "body": "dummy6_body"},
    ]
    allowed_size = 140
    expected_output = [
        [
            {"name": "dummy1", "body": "dummy1_body"},
            {"name": "dummy2", "body": "dummy2_body"},
            {"name": "dummy3", "body": "dummy3_body"},
        ],
        [
            {"name": "dummy4", "body": "dummy4_body"},
            {"name": "dummy5", "body": "dummy5_body"},
            {"name": "dummy6", "body": "dummy6_body"},
        ],
    ]

    # Execute
    returned_document = utils.split_documents_into_equal_bytes(document_to_split, allowed_size)

    # Assert
    assert returned_document == expected_output


@pytest.mark.parametrize(
    "response",
    [
        {
                "value": [
                    {
                        "id": "45b7d2e7-b882-4a80-ba97-10b7a63b8fa4",
                        "deletedDateTime": None,
                        "createdDateTime": "2018-12-22T02:21:05Z",
                        "description": "Self help community for golf",
                        "displayName": "Golf Assist",
                        "expirationDateTime": None,
                        "groupTypes": [
                            "Unified"
                        ],
                        "isAssignableToRole": "null",
                        "mail": "golfassist@contoso.com",
                        "mailNickname": "golfassist",
                        "preferredDataLocation": "CAN",
                        "renewedDateTime": "2018-12-22T02:21:05Z",
                    }
                ]
            },
    ],
)
def test_get_data_from_http_response(response):
    """
    """
    # Setup
    _, logger = settings()
    source_document = [
        {
            "id": "45b7d2e7-b882-4a80-ba97-10b7a63b8fa4",
            "deletedDateTime": None,
            "createdDateTime": "2018-12-22T02:21:05Z",
            "description": "Self help community for golf",
            "displayName": "Golf Assist",
            "expirationDateTime": None,
            "groupTypes": [
                "Unified"
            ],
            "isAssignableToRole": "null",
            "mail": "golfassist@contoso.com",
            "mailNickname": "golfassist",
            "preferredDataLocation": "CAN",
            "renewedDateTime": "2018-12-22T02:21:05Z",
        }
    ]
    error_message = 'Error while fetching the Microsoft Teams documents'

    # Execute
    target_document = utils.get_data_from_http_response(logger, response, error_message, '')

    # Assert
    assert source_document == target_document
