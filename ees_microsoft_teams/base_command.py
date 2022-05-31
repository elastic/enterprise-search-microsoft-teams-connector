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

from concurrent.futures import ThreadPoolExecutor, as_completed

from elastic_enterprise_search import WorkplaceSearch

from . import constant
from .configuration import Configuration
from .local_storage import LocalStorage
from .microsoft_teams_user_messages import MSTeamsUserMessage
from .msal_access_token import MSALAccessToken
from .permission_sync_command import PermissionSyncCommand
from .utils import get_schema_fields, split_documents_into_equal_chunks


class BaseCommand:
    """Base interface for all module commands.
    Inherit from it and implement 'execute' method, then add
    code to cli.py to register this command."""

    def __init__(self, args):
        self.args = args

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
        log_level = self.config.get_value("log_level")
        logger = logging.getLogger(__name__)
        logger.propagate = False
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
    def workplace_search_client(self):
        """Get the workplace search client instance for the running command.
        Host and api key are taken from configuration file, if
        a user was provided when running command, then basic auth
        will be used instead.
        """
        args = self.args
        host = self.config.get_value("enterprise_search.host_url")

        if hasattr(args, "user") and args.user:
            return WorkplaceSearch(
                f"{host}/api/ws/v1/sources", http_auth=(args.user, args.password)
            )
        else:
            return WorkplaceSearch(
                f"{host}/api/ws/v1/sources",
                http_auth=self.config.get_value("enterprise_search.api_key"),
            )

    @cached_property
    def config(self):
        """Get the configuration for the connector for the running command."""
        file_name = self.args.config_file
        return Configuration(file_name)

    def create_jobs(self, thread_count, func, args, iterable_list):
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

    def microsoft_user_chats_object(self, access_token):
        """Get the object for fetching the user chats related data"""
        return MSTeamsUserMessage(
            access_token, get_schema_fields, self.logger, self.config
        )

    def create_jobs_for_user_chats(
        self,
        indexing_type,
        sync_microsoft_teams,
        thread_count,
        start_time,
        end_time,
        queue,
    ):
        """Creates jobs for fetching the user chats and its children objects
        :param indexing_type: The type of the indexing i.e. Full or Incremental
        :param sync_microsoft_teams: Object for fetching the Microsoft Teams object
        :param thread_count: Thread count to make partitions
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        if "user_chats" not in self.config.get_value("objects"):
            return
        self.logger.debug(
            "Started fetching the user chats, meeting chats, and meeting recordings..."
        )
        user_chat_object = self.microsoft_user_chats_object(
            self.get_access_token()
        )
        storage_with_collection = self.local_storage.get_storage_with_collection(
            constant.USER_CHAT_DELETION_PATH
        )
        ids_list = storage_with_collection.get("global_keys")
        try:

            user_permissions, chats = sync_microsoft_teams.fetch_user_chats(
                user_chat_object, ids_list
            )
            if self.config.get_value("enable_document_permission"):
                sync_microsoft_teams.sync_permissions(user_permissions)

            chats_partition_list = split_documents_into_equal_chunks(
                chats, thread_count
            )

            user_attachment_token = MSALAccessToken(self.logger, self.config)
            user_attachment_token = user_attachment_token.get_token(
                is_acquire_for_client=True
            )
            user_drive = {}

            self.create_jobs(
                thread_count,
                sync_microsoft_teams.fetch_user_chat_messages,
                (
                    user_chat_object,
                    ids_list,
                    user_drive,
                    start_time,
                    end_time,
                    user_attachment_token,
                    False
                ),
                chats_partition_list,
            )

            storage_with_collection["global_keys"] = list(ids_list)
            self.local_storage.update_storage(
                storage_with_collection, constant.USER_CHAT_DELETION_PATH
            )

            self.logger.debug("Saving the checkpoint for User Chats")
            queue.put_checkpoint("user_chats", end_time, indexing_type)
        except Exception as exception:
            self.logger.exception(
                f"Error while indexing user chats, meeting chats and meeting recordings. Error: "
                f"{exception}"
            )
        self.logger.info(
            "Completed fetching the user chats, meeting chats and meeting recordings"
        )
