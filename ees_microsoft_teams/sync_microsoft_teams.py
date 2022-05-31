#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to sync data to Elastic Enterprise Search.

    It's possible to run full syncs and incremental syncs with this module.
"""

import csv
import os

from . import constant
from .local_storage import LocalStorage


class SyncMicrosoftTeams:
    """Fetches the Microsoft Teams documents and its permissions and store them into queue."""

    def __init__(self, indexing_type, config, logger, queue):
        self.logger = logger
        self.config = config
        self.objects = config.get_value("objects")
        self.permission = config.get_value("enable_document_permission")
        self.indexing_type = indexing_type
        self.local_storage = LocalStorage(config)
        self.queue = queue

    def fetch_user_chats(self, chats_obj, ids_list):
        """Fetches user chats from Microsoft Teams
        :param chats_obj: Chats class object to fetch the chats
        :param ids_list: Document ids list from respective doc id file
        """
        user_permissions, chats = chats_obj.get_user_chats(ids_list)
        return user_permissions, chats

    def fetch_user_chat_messages(
        self,
        chats_obj,
        ids_list,
        user_drive,
        start_time,
        end_time,
        user_attachment_token,
        is_deletion,
        chats
    ):
        """Fetches user chat messages and other chat objects from Microsoft Teams
        :param chats: List of chats to fetch its children objects
        :param chats_obj: Chats class object to fetch the chats
        :param ids_list: Document ids list from respective doc id file
        :param user_drive: User Drive to store user related details
        :param start_time: Start time for fetching the user chats data
        :param end_time: End time for fetching the user chats data
        :param user_attachment_token: Access token for fetching the user chat attachments
        """
        documents = chats_obj.get_user_chat_messages(
            ids_list, user_drive, chats, start_time, end_time, user_attachment_token
        )
        if is_deletion:
            return documents
        self.queue.append_to_queue(constant.USER_CHATS_MESSAGE, documents)
