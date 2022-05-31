#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to run an incremental sync against a Microsoft Teams Server instance.

    It will attempt to sync documents that have changed or have been added in the
    third-party system recently and ingest them into Enterprise Search instance.

    Recency is determined by the time when the last successful incremental or full job
    was ran.
"""

from . import constant
from .base_command import BaseCommand
from .checkpointing import Checkpoint
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import SyncEnterpriseSearch
from .sync_microsoft_teams import SyncMicrosoftTeams

INDEXING_TYPE = "incremental"


class IncrementalSyncCommand(BaseCommand):
    """This class start executions of incremental sync feature."""

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

        checkpoint = Checkpoint(self.logger, self.config)
        user_chats_start_time, user_chats_end_time = checkpoint.get_checkpoint(
            constant.CURRENT_TIME, "user_chats"
        )

        self.create_jobs_for_user_chats(
            INDEXING_TYPE,
            sync_microsoft_teams,
            thread_count,
            user_chats_start_time,
            user_chats_end_time,
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

        checkpoint = Checkpoint(self.logger, self.config)
        for checkpoint_data in sync_es.checkpoint_list:
            checkpoint.set_checkpoint(*checkpoint_data[:3])

    def execute(self):
        """This function execute the start function."""
        queue = ConnectorQueue(self.logger)
        self.local_storage.create_local_storage_directory()

        self.start_producer(queue)
        self.start_consumer(queue)
        self.logger.info("Completed Incremental sync")
