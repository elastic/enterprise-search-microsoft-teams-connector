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
from .checkpointing import Checkpoint
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import SyncEnterpriseSearch
from .sync_microsoft_teams import SyncMicrosoftTeams
from .msal_access_token import MSALAccessToken
from .utils import split_documents_into_equal_chunks

INDEXING_TYPE = "full"


class FullSyncCommand(BaseCommand):
    """This class starts execution of full sync feature.
        Full sync fetches the documents from the start time configured in config file till the current time
        from the Microsoft Teams and indexes them into the Workplace Search.
    """

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
        start_time = self.config.get_value("start_time")
        end_time = constant.CURRENT_TIME

        self.create_jobs_for_teams(
            INDEXING_TYPE,
            sync_microsoft_teams,
            thread_count,
            start_time,
            end_time,
            queue,
        )

        self.create_jobs_for_user_chats(
            INDEXING_TYPE,
            sync_microsoft_teams,
            thread_count,
            start_time,
            end_time,
            queue
        )

        self.create_jobs_for_calendars(
            INDEXING_TYPE, sync_microsoft_teams, start_time, end_time, queue
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
            self.config, self.logger, self.workplace_search_custom_client, queue
        )

        self.create_and_execute_jobs(thread_count, sync_es.perform_sync, (), [])
        self.logger.info("Completed indexing of the Microsoft Teams objects")

        checkpoint = Checkpoint(self.logger, self.config)
        for checkpoint_data in sync_es.checkpoint_list:
            checkpoint.set_checkpoint(checkpoint_data["checkpoint_time"], checkpoint_data["indexing_type"],
                                      checkpoint_data["object_type"])

    def execute(self):
        """This function execute the start function."""
        queue = ConnectorQueue(self.logger)
        self.local_storage.create_local_storage_directory()

        self.start_producer(queue)
        self.start_consumer(queue)
        self.logger.info("Completed Full sync")

    def create_jobs_for_teams(
        self,
        indexing_type,
        sync_microsoft_teams,
        thread_count,
        start_time,
        end_time,
        queue,
    ):
        """Creates jobs for fetching the teams and its children objects
        :param indexing_type: The type of the indexing i.e. Full or Incremental
        :param sync_microsoft_teams: Object for fetching the Microsoft Teams object
        :param thread_count: Thread count to make partitions
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        allowed_objects = [
            "teams",
            "channels",
            "channel_messages",
            "channel_tabs",
            "channel_documents",
        ]
        if not any(teams_object in self.config.get_value("object_type_to_index") for teams_object in allowed_objects):
            return

        storage_with_collection = self.local_storage.get_documents_from_doc_id_storage(
            "teams"
        )
        ids_list = storage_with_collection.get("global_keys", [])

        self.logger.debug("Started fetching the teams and its objects data...")
        microsoft_teams_object = self.microsoft_team_channel_object(
            self.get_access_token()
        )
        try:
            if self.config.get_value("enable_document_permission"):
                user_permissions = microsoft_teams_object.get_team_members()
                sync_microsoft_teams.sync_permissions(user_permissions)

            teams = sync_microsoft_teams.fetch_teams(microsoft_teams_object, ids_list)

            configuration_objects = self.config.get_value("object_type_to_index")

            teams_partition_list = split_documents_into_equal_chunks(
                teams, thread_count
            )

            channels = self.create_and_execute_jobs(
                thread_count,
                sync_microsoft_teams.fetch_channels,
                (
                    microsoft_teams_object,
                    ids_list
                ),
                teams_partition_list,
            )

            channels_partition_list = split_documents_into_equal_chunks(
                channels, thread_count
            )

            if "channel_messages" in configuration_objects:
                self.create_and_execute_jobs(
                    thread_count,
                    sync_microsoft_teams.fetch_channel_messages,
                    (
                        microsoft_teams_object,
                        start_time,
                        end_time,
                        ids_list
                    ),
                    channels_partition_list,
                )

            if "channel_tabs" in configuration_objects:
                self.create_and_execute_jobs(
                    thread_count,
                    sync_microsoft_teams.fetch_channel_tabs,
                    (
                        microsoft_teams_object,
                        start_time,
                        end_time,
                        ids_list
                    ),
                    channels_partition_list,
                )

            if "channel_documents" in configuration_objects:
                self.create_and_execute_jobs(
                    thread_count,
                    sync_microsoft_teams.fetch_channel_documents,
                    (
                        microsoft_teams_object,
                        start_time,
                        end_time,
                        ids_list
                    ),
                    teams_partition_list,
                )

            storage_with_collection["global_keys"] = list(ids_list)
            self.local_storage.update_storage(
                storage_with_collection, "teams"
            )

            self.logger.debug("Saving the checkpoint for Teams and its objects")
            queue.put_checkpoint("teams", end_time, indexing_type)
        except Exception as exception:
            self.logger.exception(
                f"Error while fetching the teams or it's objects data. Error: {exception}"
            )
        self.logger.info(
            "Completed fetching of teams and it's objects data to the Workplace Search"
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
        if "user_chats" not in self.config.get_value("object_type_to_index"):
            return
        self.logger.debug(
            "Started fetching the user chats, meeting chats, and meeting recordings..."
        )

        user_chat_object = self.microsoft_user_chats_object(
            self.get_access_token()
        )
        storage_with_collection = self.local_storage.get_documents_from_doc_id_storage(
            "user_chats"
        )
        ids_list = storage_with_collection.get("global_keys", [])

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

            self.create_and_execute_jobs(
                thread_count,
                sync_microsoft_teams.fetch_user_chat_messages,
                (
                    user_chat_object,
                    ids_list,
                    user_drive,
                    start_time,
                    end_time,
                    user_attachment_token,
                ),
                chats_partition_list,
            )

            storage_with_collection["global_keys"] = list(ids_list)
            self.local_storage.update_storage(
                storage_with_collection, "user_chats"
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

    def create_jobs_for_calendars(
        self, indexing_type, sync_microsoft_teams, start_time, end_time, queue
    ):
        """Creates jobs for fetching the calendar events
        :param indexing_type: The type of the indexing i.e. Full or Incremental
        :param sync_microsoft_teams: Object for fetching the Microsoft Teams object
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        self.logger.debug("Started fetching the calendar events from Microsoft Teams...")
        if "calendar" not in self.config.get_value("object_type_to_index"):
            return

        storage_with_collection = self.local_storage.get_documents_from_doc_id_storage("calendar")
        ids_list = storage_with_collection.get("global_keys", [])
        try:
            calendar_object = self.microsoft_calendar_object(
                self.get_access_token(is_acquire_for_client=True)
            )
            calendar_permissions = sync_microsoft_teams.fetch_calendars(
                calendar_object, ids_list, start_time, end_time
            )

            if self.config.get_value("enable_document_permission"):
                sync_microsoft_teams.sync_permissions(calendar_permissions)

            storage_with_collection["global_keys"] = list(ids_list)
            self.local_storage.update_storage(
                storage_with_collection, "calendar"
            )

            self.logger.debug("Saving the checkpoint for Calendars")
            queue.put_checkpoint("calendar", end_time, indexing_type)
        except Exception as exception:
            self.logger.exception(
                f"Error while fetching the calendars. Error: {exception}"
            )
        self.logger.info(
            "Completed fetching the calendar meetings"
        )
