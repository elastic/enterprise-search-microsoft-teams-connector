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

import functools
import logging

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

from .enterprise_search_wrapper import EnterpriseSearchWrapper
from concurrent.futures import ThreadPoolExecutor, as_completed

from .configuration import Configuration
from .local_storage import LocalStorage
from .microsoft_teams_calendars import MSTeamsCalendar
from .microsoft_teams_channels import MSTeamsChannels
from .msal_access_token import MSALAccessToken


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

    def microsoft_calendar_object(self, access_token):
        """Get the object for fetching the calendar related data"""
        return MSTeamsCalendar(
            access_token, self.logger, self.config, self.local_storage
        )
