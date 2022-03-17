#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains uncategorized utility methods.
"""

import time
import urllib.parse
from tika import parser
from bs4 import BeautifulSoup
from datetime import datetime
from . import constant

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


def check_response(logger, response, error_message, exception_message):
    """ This function is used to check and read the data received from API response
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


def insert_document_into_doc_id_storage(doc_ids_storage, id, type, parent_id, super_parent_id):
    """ This function is used to prepare item for deletion and insert into global variable.
        :param doc_ids_storage: Pass "global_keys" of microsoft_teams_user_chat_doc_ids.json, microsoft_teams_channel_chat_doc_ids.json and microsoft_teams_calendar_doc_ids.json
        :param id: Pass id of User Chat, User Chat Attachment, Calendar, Calendar Attachment,Teams, Channel Chat, Channel Chat Attachment, Channel Chat Tabs and User Chat Tabs
        :param type: Pass type of each document for deletion.
        :param parent_id: Pass parent id of each document for deletion.
        :param super_parent_id: Pass super parent id of each document for deletion
    """
    new_item = {"id": str(id), "type": type, "parent_id": str(parent_id), "super_parent_id": str(super_parent_id)}
    if new_item not in doc_ids_storage:
        return doc_ids_storage.append(new_item)
    else:
        return doc_ids_storage


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
        def execute(self, *args, **kwargs):
            retry = 1
            while retry <= self.retry_count:
                try:
                    return func(self, *args, **kwargs)
                except exception_list as exception:
                    self.logger.exception(
                        'Error while connecting to the Microsoft Teams. Retry count: %s out of %s. \
                            Error: %s' % (retry, self.retry_count, exception)
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


def get_thread_results(thread_results):
    """ Returns the documents getting from each thread
        :param thread_results: Results getting from each thread
    """
    thread_documents = []
    for result in [r.get() for r in thread_results]:
        if result:
            thread_documents.extend(result)
    return thread_documents
