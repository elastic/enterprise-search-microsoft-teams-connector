#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to sync data to Elastic Enterprise Search.

    It's possible to run full syncs and incremental syncs with this module.
"""


# from soupsieve import match
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

    def fetch_calendars(self, calendar_obj, ids_list, start_time, end_time, is_deletion):
        """Fetches calendar events from Microsoft Teams
        :param calendar_obj: Class object to fetch calendar events
        :param ids_list: Document ids list from respective doc id file
        :param start_time: Start time for fetching calendar events
        :param end_time: End time for fetching calendar events
        """
        calendar_permissions, documents = calendar_obj.get_calendars(
            ids_list, start_time, end_time
        )
        if is_deletion:
            return calendar_permissions, documents
        self.queue.append_to_queue(constant.CALENDAR, documents)
        return calendar_permissions
