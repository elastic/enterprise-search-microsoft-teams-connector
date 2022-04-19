#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run a full sync against a Microsoft Teams.

    It will attempt to sync absolutely all documents that are available in the
    third-party system and ingest them into Enterprise Search instance.
"""

from . import constant
from .base_command import BaseCommand
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import SyncEnterpriseSearch
from .sync_microsoft_teams import SyncMicrosoftTeams

INDEXING_TYPE = "full"


class FullSyncCommand(BaseCommand):
    """This class start execution of full sync feature."""

    def start_producer(self, queue):
        """This method starts async calls for the producer which is responsible for fetching documents from
        the Microsoft Teams and pushing them in the shared queue
        :param queue: Shared queue to fetch the stored documents
        """
        self.logger.debug("Starting producer for fetching objects from Microsoft Teams")

        thread_count = self.config.get_value("ms_teams_sync_thread_count")
        sync_microsoft_teams = SyncMicrosoftTeams(
            INDEXING_TYPE, self.config, self.logger, queue
        )
        sync_microsoft_teams.remove_permissions(self.workplace_search_client)

        start_time = self.config.get_value("start_time")
        end_time = constant.CURRENT_TIME

        self.create_jobs_for_user_chats(
            INDEXING_TYPE,
            sync_microsoft_teams,
            thread_count,
            start_time,
            end_time,
            queue,
        )

        for _ in range(self.config.get_value("enterprise_search_sync_thread_count")):
            queue.end_signal()

    def start_consumer(self, queue):
        """This method starts async calls for the consumer which is responsible for indexing documents to the
        Enterprise Search
        :param queue: Shared queue to fetch the stored documents
        """
        self.logger.debug("Starting consumer for indexing objects to Workplace Search")

        thread_count = self.config.get_value("enterprise_search_sync_thread_count")
        sync_es = SyncEnterpriseSearch(
            self.config, self.logger, self.workplace_search_client, queue
        )

        self.create_jobs(thread_count, sync_es.perform_sync, (), [])
        self.logger.info("Completed indexing of the Microsoft Teams objects")

    def execute(self):
        """This function execute the start function."""
        queue = ConnectorQueue(self.logger)
        self.local_storage.create_local_storage_directory()

        self.start_producer(queue)
        self.start_consumer(queue)
        self.logger.info("Completed Full sync")
