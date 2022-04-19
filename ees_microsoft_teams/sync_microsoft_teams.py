#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to sync data to Elastic Enterprise Search.

    It's possible to run full syncs and incremental syncs with this module.
"""

import csv
import multiprocessing
import os

# from soupsieve import match
from . import constant
from .local_storage import LocalStorage
from .msal_access_token import MSALAccessToken
from .permission_sync_command import PermissionSyncCommand


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

    def add_permissions_to_queue(self, user, roles):
        """This method is used to map the Microsoft Teams users to workplace search
        users and responsible to call the user permissions indexer method
        :param user: User for indexing the permissions
        :param roles: User roles
        """
        rows = {}
        mapping_sheet_path = self.config.get_value("microsoft_teams.user_mapping")
        if (
            mapping_sheet_path
            and os.path.exists(mapping_sheet_path)
            and os.path.getsize(mapping_sheet_path) > 0
        ):
            with open(mapping_sheet_path, encoding="UTF-8") as file:
                csvreader = csv.reader(file)
                for row in csvreader:
                    rows[row[0]] = row[1]
        user_name = rows.get(user, user)
        permission_dict = {"user": user_name, "roles": roles}
        self.queue.append_to_queue("permissions", permission_dict)

    def fetch_user_chats(self, chats_obj, ids_list):
        """Fetches user chats from Microsoft Teams
        :param chats_obj: Chats class object to fetch the chats
        :param ids_list: Document ids list from respective doc id file
        """
        user_permissions, chats = chats_obj.get_user_chats(ids_list)
        return user_permissions, chats

    def fetch_user_chat_messages(
        self,
        chats,
        chats_obj,
        ids_list,
        user_drive,
        start_time,
        end_time,
        user_attachment_token,
    ):
        """Fetches user chat messages and other chat objects from Microsoft Teams
        :param chats: List of chats to fetch its children objects
        :param chats_obj: Chats class object to fetch the chats
        :param ids_list: Document ids list from respective doc id file
        :param user_drive: User Drive to store user related details
        :param start_time: Start time for fetching the user chats data
        :param end_time: End time for fetching the user chats data
        :param user_attachment_token: Access token for fecthing the user chat attachments
        """
        documents = chats_obj.get_user_chat_messages(
            ids_list, user_drive, chats, start_time, end_time, user_attachment_token
        )
        return documents

    def remove_permissions(self, workplace_search_client):
        """Removes the permissions from Workplace Search"""
        if self.config.get_value("enable_document_permission"):
            PermissionSyncCommand(
                self.logger, self.config, workplace_search_client
            ).remove_all_permissions()

    def sync_permissions(self, user_permissions):
        """Sync permissions of Microsoft Objects to Workplace Search
        :param user_permissions: Dictionary having the user permissions to be indexed into
            Workplace Search
        """
        for user, permissions in user_permissions.items():
            self.add_permissions_to_queue(user, permissions)

    def perform_sync(
        self, object_type, ids_list, class_object, start_time, end_time, iterable_list
    ):
        """This method manages the multithreading in the Microsoft Teams objects
        :param object_type: Microsoft Teams objects to call the functions
        :param ids_list: Document ids list from respective doc id file
        :param class_object: Respective class objects to fetch the data
        :param iterable_list: Documents list to fetch the child objects
        :param start_time: Start time to fetch the Mircosoft Teams objects
        :param end_time: End time to fetch the Microsoft Teams objects
        """
        user_drive = multiprocessing.Manager().dict()

        if not iterable_list:
            return []

        if object_type == constant.USER_CHATS_MESSAGE:
            user_attachment_token = MSALAccessToken(self.logger, self.config)
            user_attachment_token = user_attachment_token.get_token(
                is_acquire_for_client=True
            )
            return self.fetch_user_chat_messages(
                iterable_list,
                class_object,
                ids_list,
                user_drive,
                start_time,
                end_time,
                user_attachment_token,
            )
