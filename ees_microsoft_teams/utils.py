#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains uncategorized utility methods.
"""

import time
import urllib.parse
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from tika import parser

from . import constant
from .adapter import DEFAULT_SCHEMA
from more_itertools import chunked

TIMEOUT = 400


def extract_api_response(content):
    """ Extracts the contents
        :param content: Content to be extracted
        Returns:
            parsed_test: Parsed text
    """
    parsed = parser.from_buffer(content, requestOptions={'timeout': TIMEOUT})
    parsed_text = parsed['content']
    return parsed_text


def url_encode(object_name):
    """ Performs encoding on the name of objects
        containing special characters in their url, and
        replaces single quote with two single quote since quote
        is treated as an escape character in odata
        :param object_name: Name that contains special characters
    """
    name = urllib.parse.quote(object_name, safe="'")
    return name.replace("'", "''")


def html_to_text(logger, content):
    """ This function is used to convert HTML into text
        :param logger: Logger object
        :param content: Provide html text
    """
    try:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text().strip()
        return text
    except AttributeError as exception:
        logger.exception(f"Error: {exception}")


def get_data_from_http_response(logger, response, error_message, exception_message):
    """ This function is used to get the data received from API response
        :param logger: Logger object
        :param response: Response from Microsoft Teams
        :param error_message: Error message if not getting the response
        :param exception message: Exception message
        Returns:
            Parsed response
    """
    if not response:
        logger.error(error_message)
        raise ValueError
    try:
        response_data = response.get("value")
        return response_data
    except ValueError as exception:
        logger.exception(f"{exception_message} Error: {exception}")
        raise exception


def insert_document_into_doc_id_storage(ids_list, id, type, parent_id="", super_parent_id=""):
    """ Prepares the document dictionary for deletion and insert it into the global_keys of respective doc_ids.json.
        :param ids_list: Pass "global_keys" of microsoft_teams_user_chat_doc_ids.json,
            microsoft_teams_channel_chat_doc_ids.json and microsoft_teams_calendar_doc_ids.json
        :param id: Pass id of User Chat, User Chat Attachment, Calendar, Calendar Attachment, Teams, Channel Chat,
            Channel Chat Attachment, Channel Chat Tabs and User Chat Tabs
        :param type: Pass type of each document for deletion.
        :param parent_id: Pass parent id of each document for deletion.
        :param super_parent_id: Pass super parent id of each document for deletion
    """
    new_item = {"id": str(id), "type": type, "parent_id": str(parent_id), "super_parent_id": str(super_parent_id)}
    if new_item not in ids_list:
        ids_list.append(new_item)
    return ids_list


def url_decode(text):
    """ This function is used to unquote an encoded url
        :param text: Text to be decoded
    """
    decoded_text = urllib.parse.unquote(text)
    return decoded_text


def retry(exception_list):
    """ Decorator for retrying in case of network exceptions.
        Retries the wrapped method `times` times if the exceptions listed
        in ``exceptions`` are thrown
        :param exception_list: Lists of exceptions on which the connector should retry
    """
    def decorator(func):
        """This function used as a decorator.
        """

        def execute(self, *args, **kwargs):
            """This function execute the retry logic.
            """
            retry = 1
            while retry <= self.retry_count:
                try:
                    return func(self, *args, **kwargs)
                except exception_list as exception:
                    self.logger.exception(
                        f'Error while connecting to the Microsoft Teams. Retry count: {retry} out of {self.retry_count}. \
                            Error: {exception}'
                    )
                    time.sleep(2 ** retry)
                    retry += 1
        return execute
    return decorator


def split_date_range_into_chunks(start_time, end_time, number_of_threads):
    """ Divides the timerange in equal partitions by number of threads
        :param start_time: start time of the interval
        :param end_time: end time of the interval
        :param number_of_threads: number of threads defined by user in config file
    """
    start_time = datetime.strptime(start_time, constant.DATETIME_FORMAT)
    end_time = datetime.strptime(end_time, constant.DATETIME_FORMAT)

    diff = (end_time - start_time) / number_of_threads
    datelist = []
    for idx in range(number_of_threads):
        date_time = start_time + diff * idx
        datelist.append(date_time.strftime(constant.DATETIME_FORMAT))
    formatted_end_time = end_time.strftime(constant.DATETIME_FORMAT)
    datelist.append(formatted_end_time)
    return formatted_end_time, datelist


def split_list_into_buckets(object_list, total_groups):
    """ Divides the list in groups of approximately equal sizes
        :param object_list: List to be partitioned
        :param total_groups: Number of groups to be formed
    """
    if object_list:
        groups = min(total_groups, len(object_list))
        group_list = []
        for i in range(groups):
            group_list.append(object_list[i::groups])
        return group_list
    else:
        return []


def split_documents_into_equal_chunks(documents, chunk_size):
    """This method splits a list or dictionary into equal chunks size
    :param documents: List or Dictionary to be partitioned into chunks
    :param chunk_size: Maximum size of a chunk
    Returns:
        list_of_chunks: List containing the chunks
    """
    list_of_chunks = list(chunked(documents, chunk_size))
    return list_of_chunks


def get_thread_results(thread_results):
    """ Returns the documents getting from each thread
        :param thread_results: Results getting from each thread
    """
    thread_documents = []
    for result in [r.get() for r in thread_results]:
        if result:
            thread_documents.extend(result)
    return thread_documents


def get_schema_fields(document_name, objects):
    """ Returns the schema of all the include_fields or exclude_fields specified in the configuration file.
        :param document_name: Document name from Teams, Channels, Channel Messages, User Chats, etc.
        Returns:
            schema: Included and excluded fields schema
    """
    fields = objects.get(document_name)
    adapter_schema = DEFAULT_SCHEMA[document_name]
    field_id = adapter_schema['id']
    if fields:
        include_fields = fields.get("include_fields")
        exclude_fields = fields.get("exclude_fields")
        if include_fields:
            adapter_schema = {
                key: val for key, val in adapter_schema.items() if val in include_fields}
        elif exclude_fields:
            adapter_schema = {
                key: val for key, val in adapter_schema.items() if val not in exclude_fields}
        adapter_schema['id'] = field_id
    return adapter_schema


def get_records_by_types(documents):
    """Groups the documents based on their object type
        :param document: Documents to be indexed
        Returns:
            data_frame_dict: Dictionary of type with its count
    """
    if documents:
        data_frame = pd.DataFrame(documents)
        data_frame_size = data_frame.groupby('type').size()
        data_frame_dict = data_frame_size.to_dict()
        return data_frame_dict
    return {}


def is_document_in_present_data(document, document_id, key):
    """ Filters the child item while iterating over the document.
        :param document: Document for comparision
        :param document_id: Document id for comparision with doc_id document
        :param key: Key for fetching the value
    """
    return document[key] == document_id
