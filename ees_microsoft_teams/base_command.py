#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Module contains a base command interface.

    Connector can run multiple commands such as full-sync, incremental-sync,
    etc. This module provides convenience interface defining the shared
    objects and methods that will can be used by commands.
"""

import csv
import functools
import logging
import os

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

from .enterprise_search_wrapper import EnterpriseSearchWrapper
from concurrent.futures import ThreadPoolExecutor, as_completed

from elastic_enterprise_search import __version__
from packaging import version

from .configuration import Configuration
from .local_storage import LocalStorage
from .microsoft_teams_calendars import MSTeamsCalendar
from .microsoft_teams_channels import MSTeamsChannels
from .microsoft_teams_user_messages import MSTeamsUserMessage
from .msal_access_token import MSALAccessToken
from .permission_sync_command import PermissionSyncCommand

ENTERPRISE_V8 = version.parse("8.0")


class BaseCommand:
    """Base interface for all module commands.
    Inherit from it and implement 'execute' method, then add
    code to cli.py to register this command."""

    def __init__(self, args):
        self.args = args
        self.version = version.parse(__version__)

    def execute(self):
        """Run the command.
        This method is overridden by actual commands with logic
        that is specific to each command implementing it."""
        raise NotImplementedError

    @cached_property
    def logger(self):
        """Get the logger instance for the running command.
        log level will be determined by the configuration
        setting log_level.
        """
        log_level = self.config.get_value('log_level')
        logger = logging.getLogger(__name__)
        logger.propagate = True
        logger.setLevel(log_level)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s Thread[%(thread)s]: %(message)s")
        handler.setFormatter(formatter)
        # Uncomment the following lines to output logs in ECS-compatible format
        # formatter = ecs_logging.StdlibFormatter()
        # handler.setFormatter(formatter)
        handler.setLevel(log_level)
        logger.addHandler(handler)

        return logger

    @cached_property
    def workplace_search_custom_client(self):
        """Get the workplace search custom client instance for the running command."""
        return EnterpriseSearchWrapper(self.logger, self.config, self.args)

    @cached_property
    def config(self):
        """Get the configuration for the connector for the running command."""
        file_name = self.args.config_file
        return Configuration(file_name)

    def create_and_execute_jobs(self, thread_count, func, args, iterable_list):
        """Creates a thread pool of given number of thread count
        :param thread_count: Total number of threads to be spawned
        :param func: The target function on which the async calls would be made
        :param args: Arguments for the targeted function
        :param iterable_list: List to iterate over and create thread
        """

        callables = []
        if iterable_list:
            for list_element in iterable_list:
                callables.append(functools.partial(func, *args, list_element))
        else:
            callables.append(func)

        documents = []
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_path = {
                executor.submit(list_element): list_element
                for list_element in callables
            }
            for future in as_completed(future_to_path):
                try:
                    if future.result():
                        documents.extend(future.result())
                except Exception as exception:
                    self.logger.exception(
                        f"Error while fetching the data from Microsoft Teams. Error {exception}"
                    )
        return documents

    @cached_property
    def local_storage(self):
        """Get the object for local storage to fetch and update ids stored locally"""
        return LocalStorage(self.logger)

    def get_access_token(self, is_acquire_for_client=False):
        """Get access token for fetching the data
        :param is_acquire_for_client: Flag for fetching the access token
        """
        return MSALAccessToken(self.logger, self.config).get_token(is_acquire_for_client)

    def microsoft_team_channel_object(self, access_token):
        """Get the object for fetching the teams and its children"""
        return MSTeamsChannels(
            access_token, self.logger, self.config, self.local_storage
        )

    def microsoft_user_chats_object(self, access_token):
        """Get the object for fetching the user chats related data"""
        return MSTeamsUserMessage(
            access_token, self.logger, self.config, self.local_storage
        )

    def microsoft_calendar_object(self, access_token):
        """Get the object for fetching the calendar related data"""
        return MSTeamsCalendar(
            access_token, self.logger, self.config, self.local_storage
        )

    def get_mapped_users(self):
        """Returns mapped users from the CSV file
        """
        rows = {}
        mapping_sheet_path = self.config.get_value("microsoft_teams.user_mapping")
        if (
            mapping_sheet_path and os.path.exists(mapping_sheet_path) and os.path.getsize(mapping_sheet_path) > 0
        ):
            with open(mapping_sheet_path, encoding="UTF-8") as file:
                for row in csv.reader(file):
                    rows[row[0]] = row[1]
        return rows

    def manage_permissions(self, object_permissions, ws_user, ws_permissions):
        """Returns the permissions differs from Workplace Search
        :param object_permissions: Permissions of the Microsoft Teams Object
        :param ws_user: Workplace Search user
        :param ws_permissions: Workplace Search permissions of a user
        """
        mapped_users = self.get_mapped_users()
        for ms_team_user, permissions in object_permissions.items():
            ms_team_user = mapped_users.get(ms_team_user, ms_team_user)
            if ms_team_user.lower() == ws_user.lower():
                ws_permissions = set(ws_permissions).difference(permissions)
        return list(ws_permissions)

    def remove_object_permissions(self, end_time):
        """Remove the permissions of the users removed from the Microsoft Teams objects
        :param end_time: End time to fetch the permissions
        """
        deleted_permissions_list = []
        microsoft_teams_object = self.microsoft_team_channel_object(
            self.get_access_token()
        )
        user_chat_object = self.microsoft_user_chats_object(
            self.get_access_token()
        )
        calendar_object = self.microsoft_calendar_object(
            self.get_access_token(is_acquire_for_client=True)
        )

        teams_permissions = microsoft_teams_object.get_team_members()
        user_chats_permissions, _ = user_chat_object.get_user_chats([])
        calendar_permissions, _ = calendar_object.get_calendars([], self.config.get_value('start_time'), end_time)

        ws_user_permissions = PermissionSyncCommand(
            self.logger, self.config, self.workplace_search_custom_client
        ).list_user_permissions()

        for ws_user, ws_permissions in ws_user_permissions.items():
            actual_permissions = ws_permissions
            ws_permissions = self.manage_permissions(teams_permissions, ws_user, ws_permissions)
            ws_permissions = self.manage_permissions(user_chats_permissions, ws_user, ws_permissions)
            ws_permissions = self.manage_permissions(calendar_permissions, ws_user, ws_permissions)
            deleted_permissions_list.append({"user": ws_user, "actual_permissions": actual_permissions,
                                            "deleted_permissions": ws_permissions})
        for permission_dict in deleted_permissions_list:
            if permission_dict["deleted_permissions"]:
                if self.version >= ENTERPRISE_V8:
                    self.workplace_search_custom_client.remove_permissions(
                        {
                            "external_user_properties": [{'attribute_value': permission_dict['user']}],
                            "permissions": permission_dict['deleted_permissions']
                        }
                    )
                else:
                    self.workplace_search_custom_client.remove_permissions(
                        {"user": permission_dict['user'], "permissions": permission_dict['deleted_permissions']}
                    )
                self.workplace_search_custom_client.add_permissions(
                    permission_dict['user'],
                    list(set(permission_dict['actual_permissions']) - set(permission_dict['deleted_permissions']))
                )
                self.logger.debug(
                    f"Removed permissions for {permission_dict['user']} from the Workplace Search"
                )
            else:
                self.logger.debug(
                    f"No permission found for {permission_dict['user']} to remove from Workplace Search"
                )
