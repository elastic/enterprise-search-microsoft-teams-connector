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

from .local_storage import LocalStorage
from .permission_sync_command import PermissionSyncCommand
from . import constant


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
            mapping_sheet_path and os.path.exists(mapping_sheet_path) and os.path.getsize(mapping_sheet_path) > 0
        ):
            with open(mapping_sheet_path, encoding="UTF-8") as file:
                csvreader = csv.reader(file)
                for row in csvreader:
                    rows[row[0]] = row[1]
        user_name = rows.get(user, user)
        permission_dict = {"user": user_name, "roles": roles}
        self.queue.append_to_queue("permissions", permission_dict)

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
        :param user_attachment_token: Access token for fecthing the user chat attachments
        """
        documents = chats_obj.get_user_chat_messages(
            ids_list, user_drive, chats, start_time, end_time, user_attachment_token
        )
        if is_deletion:
            return documents
        self.queue.append_to_queue(constant.USER_CHATS_MESSAGE, documents)

    def fetch_teams(self, teams_obj, ids_list, is_deletion):
        """Fetches teams from Microsoft Teams
        :param teams_obj: Class object to fetch teams and its objects
        :param ids_list: Document ids list from respective doc id file
        """
        teams = teams_obj.get_all_teams(ids_list)
        if not is_deletion:
            self.queue.append_to_queue(constant.TEAMS, teams)
        return teams

    def fetch_channels(self, teams_obj, ids_list, is_deletion, teams):
        """Fetches channels from Microsoft Teams
        :param teams: List of teams to fetch the channels
        :param teams_obj: Class object to fetch teams and its objects
        :param ids_list: Document ids list from respective doc id file
        """
        channels, channel_documents = teams_obj.get_team_channels(teams, ids_list)
        if is_deletion:
            return [{"channels": channels, "channel_documents": channel_documents}]
        self.queue.append_to_queue(constant.CHANNELS, channel_documents)
        return channels

    def fetch_channel_documents(self, teams_obj, start_time, end_time, ids_list, is_deletion, teams):
        """Fetches channel documents from Microsoft Teams
        :param teams: List of teams to fetch channels from Microsoft Teams
        :param teams_obj: Class object to fetch teams and its objects
        :param start_time: Start time for fetching channel documents
        :param end_time: End time for fetching channel documents
        :param ids_list: Document ids list from respective doc id file
        """
        channel_documents = teams_obj.get_channel_documents(
            teams, ids_list, start_time, end_time
        )
        if is_deletion:
            return channel_documents
        self.queue.append_to_queue(constant.CHANNEL_DOCUMENTS, channel_documents)

    def fetch_channel_messages(
        self, teams_obj, start_time, end_time, ids_list, is_deletion, channels
    ):
        """Fetches channel messages from Microsoft Teams
        :param channels: List of channels to fetch channel messages and tabs from Microsoft Teams
        :param teams_obj: Class object to fetch teams and its objects
        :param start_time: Start time for fetching channel messages and tabs
        :param end_time: End time for fetching channel messages and tabs
        :param ids_list: Document ids list from respective doc id file
        """
        channel_message_documents = teams_obj.get_channel_messages(
            channels, ids_list, start_time, end_time
        )
        if is_deletion:
            return channel_message_documents
        self.queue.append_to_queue(constant.CHANNEL_MESSAGES, channel_message_documents)

    def fetch_channel_tabs(self, teams_obj, start_time, end_time, ids_list, is_deletion, channels):
        """Fetches channel tabs from Microsoft Teams
        :param channels: List of channels to fetch channel messages and tabs from Microsoft Teams
        :param teams_obj: Class object to fetch teams and its objects
        :param start_time: Start time for fetching channel messages and tabs
        :param end_time: End time for fetching channel messages and tabs
        :param ids_list: Document ids list from respective doc id file
        """
        tab_documents = teams_obj.get_channel_tabs(
            channels, ids_list, start_time, end_time
        )
        if is_deletion:
            return tab_documents
        self.queue.append_to_queue(constant.CHANNEL_TABS, tab_documents)

    def remove_permissions(self, workplace_search_client):
        """Removes the permissions from Workplace Search"""
        if self.config.get_value("enable_document_permission"):
            PermissionSyncCommand(
                self.logger, self.config, workplace_search_client
            ).remove_all_permissions()
        else:
            self.logger.info("'enable_document_permission' is disabled, skipping permission removal")

    def sync_permissions(self, user_permissions):
        """Sync permissions of Microsoft Objects to Workplace Search
        :param user_permissions: Dictionary having the user permissions to be indexed into
            Workplace Search
        """
        for user, permissions in user_permissions.items():
            self.add_permissions_to_queue(user, permissions)
