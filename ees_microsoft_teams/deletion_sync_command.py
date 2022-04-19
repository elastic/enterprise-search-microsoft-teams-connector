#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in Microsoft Teams will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""
from .base_command import BaseCommand
from .connector_queue import ConnectorQueue
from .sync_enterprise_search import SyncEnterpriseSearch
from .sync_microsoft_teams import SyncMicrosoftTeams
from . import constant
from .utils import split_documents_into_equal_chunks, is_document_in_present_data


INDEXING_TYPE = "full"


class DeletionSyncCommand(BaseCommand):
    """This class start execution of deletion feature.
    """

    def remove_deleted_documents_from_global_keys(self, live_documents, list_ids_documents, deleted_documents, global_keys_documents,
                                                  parent_id, super_parent_id):
        """ Updates the local storage with removing the keys that were deleted from Microsoft Teams
            :param live_documents: Documents present in Microsoft Teams
            :param list_ids_documents: Documents present in respective doc_ids.json files
            :param deleted_documents: Document list that were deleted from Microsoft Teams
            :param global_keys_documents: Document list that are present in doc_ids.json
            :param parent_id: Parent id of the document
            :param super_parent_id: Super parent id of the document
        """
        parent_items = list(filter(lambda seq: is_document_in_present_data(
            seq, parent_id, "parent_id"), list_ids_documents))
        for item in parent_items:
            item_id = item["id"]
            parent_id = item["parent_id"]
            super_parent_id = item["super_parent_id"]
            type = item["type"]
            present_items = list(filter(
                lambda seq: is_document_in_present_data(seq, item_id, "id"), live_documents))
            if(len(present_items) == 0 and type not in [
                    constant.CHATS, constant.USER, constant.USER_CHAT_DRIVE, constant.USER_CHAT_DRIVE_ITEM,
                    constant.CHANNEL_DRIVE, constant.CHANNEL_ROOT, constant.CHANNEL_DRIVE_ITEM]):
                deleted_documents.append(item_id)
                if item in global_keys_documents:
                    global_keys_documents.remove(item)

            # Recursively call the function
            self.remove_deleted_documents_from_global_keys(live_documents, list_ids_documents,
                                                           deleted_documents, global_keys_documents, item_id, super_parent_id)

    def create_jobs_for_teams(self, sync_microsoft_teams, thread_count, start_time, end_time, queue):
        """Creates jobs for deleting the teams and its children objects
        :param sync_microsoft_teams: Object for fetching the Microsoft Teams object
        :param thread_count: Thread count to make partitions
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        allowed_objects = ["teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]
        storage_with_collection = self.local_storage.get_storage_with_collection(constant.CHANNEL_CHAT_DELETION_PATH)

        if not any(teams_object in self.config.get_value("objects") for teams_object in allowed_objects):
            return
        self.logger.debug("Started deleting the teams and its objects data...")
        microsoft_teams_object = self.microsoft_team_channel_object(self.get_access_token())
        try:
            deleted_data = storage_with_collection.get("delete_keys") or []
            global_keys_documents = storage_with_collection.get("global_keys") or []
            teams, channels, channel_index_documents = sync_microsoft_teams.fetch_teams_and_channels(
                microsoft_teams_object, [])
            live_data = []
            delete_keys_documents = []

            configuration_objects = self.config.get_value("objects")
            if "teams" in configuration_objects:
                live_data.extend(teams)
            if "channels" in configuration_objects:
                live_data.extend(channel_index_documents)

            teams_partition_list = split_documents_into_equal_chunks(teams, thread_count)
            channels_partition_list = split_documents_into_equal_chunks(channels, thread_count)

            if "channel_messages" in configuration_objects:
                channel_messages = self.create_jobs(
                    thread_count, sync_microsoft_teams.perform_sync,
                    (constant.CHANNEL_MESSAGES, [], microsoft_teams_object, start_time, end_time,),
                    channels_partition_list
                )
                live_data.extend(channel_messages)

            if "channel_tabs" in configuration_objects:
                channel_tabs = self.create_jobs(
                    thread_count, sync_microsoft_teams.perform_sync,
                    (constant.CHANNEL_TABS, [], microsoft_teams_object, start_time, end_time,),
                    channels_partition_list
                )
                live_data.extend(channel_tabs)

            if "channel_documents" in configuration_objects:
                channel_documents = self.create_jobs(
                    thread_count, sync_microsoft_teams.perform_sync,
                    (constant.CHANNEL_DOCUMENTS, [], microsoft_teams_object, start_time, end_time,),
                    teams_partition_list
                )
                live_data.extend(channel_documents)
            self.remove_deleted_documents_from_global_keys(live_data, deleted_data,
                                                           delete_keys_documents, global_keys_documents, "", "")
            queue.append_to_queue('deletion', list(delete_keys_documents))
            storage_with_collection["global_keys"] = list(global_keys_documents)
            storage_with_collection['delete_keys'] = []
            self.local_storage.update_storage(storage_with_collection, constant.CHANNEL_CHAT_DELETION_PATH)
        except Exception as exception:
            self.logger.exception(f"Error while deleting the teams or it's objects data. Error: {exception}")
        self.logger.info("Completed deleting of teams and it's objects data to the Workplace Search")

    def create_jobs_for_user_chats(self, sync_microsoft_teams, thread_count, start_time, end_time, queue):
        """Creates jobs for deleting the user chats and its children objects
        :param sync_microsoft_teams: Object for fetching the Microsoft Teams object
        :param thread_count: Thread count to make partitions
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        if "user_chats" not in self.config.get_value('objects'):
            return
        self.logger.debug("Started deletion the user chats, meeting chats, and meeting recordings...")
        user_chat_object = self.microsoft_user_chats_object(self.get_access_token())
        storage_with_collection = self.local_storage.get_storage_with_collection(constant.USER_CHAT_DELETION_PATH)
        try:
            _, chats = sync_microsoft_teams.fetch_user_chats(user_chat_object, [])
            chats_partition_list = split_documents_into_equal_chunks(chats, thread_count)
            chat_messages_documents = self.create_jobs(
                thread_count, sync_microsoft_teams.perform_sync,
                (constant.USER_CHATS_MESSAGE, [], user_chat_object, start_time, end_time,),
                chats_partition_list
            )
            deleted_data = storage_with_collection.get("delete_keys") or []
            global_keys_documents = storage_with_collection.get("global_keys") or []
            delete_keys_documents = []
            self.remove_deleted_documents_from_global_keys(chat_messages_documents, deleted_data,
                                                           delete_keys_documents, global_keys_documents, "", "")
            queue.append_to_queue('deletion', list(delete_keys_documents))
            storage_with_collection["global_keys"] = list(global_keys_documents)
            storage_with_collection['delete_keys'] = []
            self.local_storage.update_storage(storage_with_collection, constant.USER_CHAT_DELETION_PATH)
        except Exception as exception:
            self.logger.exception(
                f"Error while deleting user chats, meeting chats and meeting recordings. Error: "
                f"{exception}")
        self.logger.info("Completed deleting the user chats, meeting chats and meeting recordings")

    def create_jobs_for_calendars(self, sync_microsoft_teams, start_time, end_time, queue):
        """Creates jobs for deleting the calendar events
        :param sync_microsoft_teams: Object for fetching the Microsoft Teams object
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        if "calendar" not in self.config.get_value("objects"):
            return
        self.logger.debug("Started deleting the calendar events from Microsoft Teams...")
        storage_with_collection = self.local_storage.get_storage_with_collection(constant.CALENDAR_CHAT_DELETION_PATH)
        try:
            calendar_object = self.microsoft_calendar_object(self.get_access_token(is_acquire_for_client=True))
            _, documents = sync_microsoft_teams.fetch_calendars(calendar_object, [], start_time, end_time)
            deleted_data = storage_with_collection.get("delete_keys") or []
            global_keys_documents = storage_with_collection.get("global_keys") or []
            delete_keys_documents = []
            self.remove_deleted_documents_from_global_keys(documents, deleted_data,
                                                           delete_keys_documents, global_keys_documents, "", "")
            queue.append_to_queue('deletion', list(delete_keys_documents))
            storage_with_collection["global_keys"] = list(global_keys_documents)
            storage_with_collection['delete_keys'] = []
            self.local_storage.update_storage(storage_with_collection, constant.CALENDAR_CHAT_DELETION_PATH)
        except Exception as exception:
            self.logger.exception(f"Error while deleting the calendars. Error: {exception}")
        self.logger.info("Completed deleting the calendar events from Microsoft Teams")

    def start_producer(self, queue):
        """This method starts async calls for the producer which is responsible
        for fetching documents from the Microsoft Teams and pushing them in the shared queue
        :param queue: Shared queue to store the fetched documents
        """
        self.logger.debug("Starting producer for deleting objects from Microsoft Teams")

        thread_count = self.config.get_value("ms_teams_sync_thread_count")
        sync_microsoft_teams = SyncMicrosoftTeams(INDEXING_TYPE, self.config, self.logger, queue)
        start_time = self.config.get_value("start_time")
        end_time = constant.CURRENT_TIME

        self.create_jobs_for_teams(sync_microsoft_teams, thread_count, start_time, end_time, queue)
        self.create_jobs_for_user_chats(sync_microsoft_teams, thread_count, start_time, end_time, queue)
        self.create_jobs_for_calendars(sync_microsoft_teams, start_time, end_time, queue)

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
            self.config, self.logger, self.workplace_search_client, queue
        )

        self.create_jobs(thread_count, sync_es.perform_sync, (), [])
        self.logger.info("Completed deletion of the Microsoft Teams objects")

    def execute(self):
        """This function execute the start function.
        """
        queue = ConnectorQueue(self.logger)
        self.start_producer(queue)
        self.start_consumer(queue)
        self.logger.info("Completed Deletion sync")
