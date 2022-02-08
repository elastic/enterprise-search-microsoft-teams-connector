# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import urllib.parse
from tika import parser
from bs4 import BeautifulSoup


def print_and_log(logger, level, message):
    """ Prints the log messages
        :param logger: Logger name
        :param level: Log level
        :param message: Log message
    """
    print(message)
    getattr(logger, level.lower())(message)


def extract_api_response(content):
    """ Extracts the contents
        :param content: Content to be extracted
        Returns:
            parsed_test: Parsed text
    """
    parsed = parser.from_buffer(content)
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
        :param content: Provide html text
    """
    try:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text().strip()
        return text
    except Exception as exception:
        logger.exception(f"Error while converting HTML into text. Error: {exception}")


def check_response(logger, response, error_message, exception_message):
    """ This function is used to check and read the data received from API response
        :param response: Response from MS Teams
        :param error_message: Error message if not getting the response
        :param exception message: Exception message
        Returns:
            Parsed response, and is_error flag
    """
    if not response:
        logger.error(error_message)
        return (None, True)
    try:
        response_data = response.get("value")
        return (response_data, False)
    except ValueError as exception:
        logger.exception("%s Error: %s" % (exception_message, exception))
        return (None, True)


def insert_document_into_doc_id_storage(doc_ids_storage, id, type, parent_id, super_parent_id):
    """ This function is used to prepare item for deindexing and insert into global variable.
        :param doc_ids_storage: Pass "global_keys" of ms_teams_user_chat_doc_ids.json, ms_teams_channel_chat_doc_ids.json and ms_teams_calendar_doc_ids.json
        :param id: Pass id of User Chat, User Chat Attachment, Calendar, Calendar Attachment,Teams, Channel Chat, Channel Chat Attachment, Channel Chat Tabs and User Chat Tabs
        :param type: Pass type of each document for deindexing.
        :param parent_id: Pass parent id of each document for deindexing.
        :param super_parent_id: Pass super parent id of each document for deindexing
    """
    new_item = {"id": str(id), "type": type, "parent_id": str(parent_id), "super_parent_id": str(super_parent_id)}
    if new_item not in doc_ids_storage:
        return doc_ids_storage.append(new_item)
    else:
        return doc_ids_storage
