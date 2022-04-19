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

    def fetch_calendars(self, calendar_obj, ids_list, start_time, end_time):
        """Fetches calendar events from Microsoft Teams
        :param calendar_obj: Class object to fetch calendar events
        :param ids_list: Document ids list from respective doc id file
        :param start_time: Start time for fetching calendar events
        :param end_time: End time for fetching calendar events
        """
        calendar_permissions, documents = calendar_obj.get_calendars(
            ids_list, start_time, end_time
        )
        return calendar_permissions, documents

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
