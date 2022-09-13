#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in Microsoft Teams will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""
from . import constant
from .deletion_command import DeletionCommand
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import SyncEnterpriseSearch

INDEXING_TYPE = "full"


class DeletionSyncCommand(DeletionCommand):
    """This class start execution of deletion feature.
    """
    def start_producer(self, queue):
        """This method starts async calls for the producer which is responsible
        for fetching documents from the Microsoft Teams and pushing them in the shared queue
        :param queue: Shared queue to store the fetched documents
        """
        self.logger.debug("Starting producer for deleting objects from Microsoft Teams")

        thread_count = self.config.get_value("ms_teams_sync_thread_count")
        start_time = self.config.get_value("start_time")
        end_time = constant.CURRENT_TIME

        self.create_jobs_for_teams(thread_count, start_time, end_time, queue)
        self.create_jobs_for_user_chats(thread_count, start_time, end_time, queue)
        self.create_jobs_for_calendars(start_time, end_time, queue)

        for _ in range(self.config.get_value("enterprise_search_sync_thread_count")):
            queue.end_signal()

    def start_consumer(self, queue):
        """This method starts async calls for the consumer which is responsible for indexing documents to the
        Enterprise Search
        :param queue: Shared queue to fetch the stored documents
        """
        self.logger.debug("Starting consumer for deleting objects to Workplace Search")

        thread_count = self.config.get_value("enterprise_search_sync_thread_count")
        sync_es = SyncEnterpriseSearch(
            self.config, self.logger, self.workplace_search_custom_client, queue
        )

        self.create_and_execute_jobs(thread_count, sync_es.perform_sync, (), [])
        self.logger.info("Completed deletion of the Microsoft Teams objects")

    def execute(self):
        """This function execute the start function.
        """
        queue = ConnectorQueue(self.logger)
        self.start_producer(queue)
        self.start_consumer(queue)
        self.logger.info("Completed Deletion sync")
