#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to sync data to Elastic Enterprise Search.

    It's possible to run full syncs and incremental syncs with this module.
"""

from . import constant
from .local_storage import LocalStorage


class SyncMicrosoftTeams:
    """Fetches the Microsoft Teams documents and its permissions and store them into queue."""

    def __init__(self, indexing_type, config, logger, queue):
        self.logger = logger
        self.config = config
        self.objects = config.get_value("object_type_to_index")
        self.permission = config.get_value("enable_document_permission")
        self.indexing_type = indexing_type
        self.local_storage = LocalStorage(config)
        self.queue = queue

    def fetch_teams(self, teams_obj, ids_list, is_deletion):
        """Fetches teams from Microsoft Teams
        :param teams_obj: Class object to fetch teams and its objects
        :param ids_list: Document ids list from respective doc id file
        :param is_deletion: Flag to check if the function is used for deletion
        """
        teams = teams_obj.get_all_teams(ids_list)
        if not is_deletion and "teams" in self.objects:
            self.queue.append_to_queue(constant.TEAMS, teams)
        return teams

    def fetch_channels(self, teams_obj, ids_list, is_deletion, teams):
        """Fetches channels from Microsoft Teams
        :param teams: List of teams to fetch the channels
        :param teams_obj: Class object to fetch teams and its objects
        :param ids_list: Document ids list from respective doc id file
        :param is_deletion: Flag to check if the function is used for deletion
        """
        channels, channel_documents = teams_obj.get_team_channels(teams, ids_list)
        if is_deletion:
            return [{"channels": channels, "channel_documents": channel_documents}]
        if "channels" in self.objects:
            self.queue.append_to_queue(constant.CHANNELS, channel_documents)
        return channels
