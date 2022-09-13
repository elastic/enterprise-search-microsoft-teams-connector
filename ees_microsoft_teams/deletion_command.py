#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module is used to create multithreading jobs for Microsoft Teams objects.
"""
from . import constant
from .base_command import BaseCommand
from .msal_access_token import MSALAccessToken
from .sync_microsoft_teams import SyncMicrosoftTeams
from .utils import split_documents_into_equal_chunks, is_document_in_present_data


class DeletionCommand(BaseCommand):
    """ This class creates the multithreading jobs for Teams, User Chats and Calendars objects
    """
    def create_jobs_for_teams(self, thread_count, start_time, end_time, queue):
        """Creates jobs for deleting the teams and its children objects
        :param thread_count: Thread count to make partitions
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        allowed_objects = ["teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]
        storage_with_collection = self.local_storage.get_documents_from_doc_id_storage("teams")
        sync_ms_teams_obj = SyncMicrosoftTeams("deletion_sync", self.config, self.logger, queue)

        if not any(teams_object in self.config.get_value("object_type_to_index") for teams_object in allowed_objects):
            return

        self.logger.debug("Started deleting the teams and its objects data...")
        microsoft_teams_object = self.microsoft_team_channel_object(self.get_access_token())
        try:
            deleted_data = storage_with_collection.get("delete_keys") or []
            global_keys_documents = storage_with_collection.get("global_keys") or []

            teams = microsoft_teams_object.get_all_teams([])
            teams_partition_list = split_documents_into_equal_chunks(
                teams, thread_count
            )

            job_documents_list = self.create_and_execute_jobs(
                thread_count,
                sync_ms_teams_obj.fetch_channels_for_deletion,
                (microsoft_teams_object,),
                teams_partition_list,
            )

            channels, channel_index_documents = [], []
            for channel_data in job_documents_list:
                channels.extend(channel_data["channels"])
                channel_index_documents.extend(channel_data["channel_documents"])

            live_data = []
            delete_keys_documents = []

            configuration_objects = self.config.get_value("object_type_to_index")
            if "teams" in configuration_objects:
                live_data.extend(teams)
            if "channels" in configuration_objects:
                live_data.extend(channel_index_documents)

            channels_partition_list = split_documents_into_equal_chunks(channels, thread_count)

            if "channel_messages" in configuration_objects:
                channel_messages = self.create_and_execute_jobs(
                    thread_count, sync_ms_teams_obj.fetch_channel_messages_for_deletion,
                    (microsoft_teams_object, start_time, end_time, []),
                    channels_partition_list
                )
                live_data.extend(channel_messages)

            if "channel_tabs" in configuration_objects:
                channel_tabs = self.create_and_execute_jobs(
                    thread_count, sync_ms_teams_obj.fetch_channel_tabs_for_deletion,
                    (microsoft_teams_object, start_time, end_time, []),
                    channels_partition_list
                )
                live_data.extend(channel_tabs)

            if "channel_documents" in configuration_objects:
                channel_documents = self.create_and_execute_jobs(
                    thread_count, sync_ms_teams_obj.fetch_channel_documents_for_deletion,
                    (microsoft_teams_object, start_time, end_time, []),
                    teams_partition_list
                )
                live_data.extend(channel_documents)

            self.remove_deleted_documents_from_global_keys(
                live_data, deleted_data, delete_keys_documents, global_keys_documents, "", ""
            )

            queue.append_to_queue("deletion", list(delete_keys_documents))
            storage_with_collection["global_keys"] = list(global_keys_documents)
            storage_with_collection["delete_keys"] = []
            self.local_storage.update_storage(storage_with_collection, "teams")

        except Exception as exception:
            self.logger.exception(f"Error while deleting the teams or it's objects data. Error: {exception}")
        self.logger.info("Completed deleting of teams and it's objects data to the Workplace Search")

    def create_jobs_for_user_chats(self, thread_count, start_time, end_time, queue):
        """Creates jobs for deleting the user chats and its children objects
        :param thread_count: Thread count to make partitions
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        if "user_chats" not in self.config.get_value('object_type_to_index'):
            return

        self.logger.debug("Started deletion the user chats, meeting chats, and meeting recordings...")
        user_chat_object = self.microsoft_user_chats_object(self.get_access_token())
        storage_with_collection = self.local_storage.get_documents_from_doc_id_storage("user_chats")
        sync_ms_teams_obj = SyncMicrosoftTeams("deletion_sync", self.config, self.logger, queue)

        try:
            user_drive = {}
            _, chats = user_chat_object.get_user_chats(ids_list=[])
            chats_partition_list = split_documents_into_equal_chunks(chats, thread_count)

            user_attachment_token = MSALAccessToken(self.logger, self.config)
            user_attachment_token = user_attachment_token.get_token(
                is_acquire_for_client=True
            )

            chat_messages_documents = self.create_and_execute_jobs(
                thread_count, sync_ms_teams_obj.fetch_user_chat_messages_for_deletion,
                (user_chat_object, [], user_drive, start_time, end_time, user_attachment_token),
                chats_partition_list
            )

            deleted_data = storage_with_collection.get("delete_keys") or []
            global_keys_documents = storage_with_collection.get("global_keys") or []

            delete_keys_documents = []
            self.remove_deleted_documents_from_global_keys(
                chat_messages_documents, deleted_data, delete_keys_documents, global_keys_documents, "", ""
            )
            queue.append_to_queue("deletion", list(delete_keys_documents))
            storage_with_collection["global_keys"] = list(global_keys_documents)
            storage_with_collection["delete_keys"] = []
            self.local_storage.update_storage(storage_with_collection, "user_chats")

        except Exception as exception:
            self.logger.exception(
                f"Error while deleting user chats, meeting chats and meeting recordings. Error: "
                f"{exception}"
            )
        self.logger.info("Completed deleting the user chats, meeting chats and meeting recordings")

    def create_jobs_for_calendars(self, start_time, end_time, queue):
        """Creates jobs for deleting the calendar events
        :param start_time: Start time for fetching the data
        :param end_time: End time for fetching the data
        :param queue: Shared queue for storing the data
        """
        if "calendar" not in self.config.get_value("object_type_to_index"):
            return

        self.logger.debug("Started deleting the calendar events from Microsoft Teams...")
        storage_with_collection = self.local_storage.get_documents_from_doc_id_storage("calendar")
        try:
            calendar_object = self.microsoft_calendar_object(self.get_access_token(is_acquire_for_client=True))
            _, documents = calendar_object.get_calendars(ids_list=[], start_time=start_time, end_time=end_time)

            deleted_data = storage_with_collection.get("delete_keys") or []
            global_keys_documents = storage_with_collection.get("global_keys") or []

            delete_keys_documents = []
            self.remove_deleted_documents_from_global_keys(
                documents, deleted_data, delete_keys_documents, global_keys_documents, "", ""
            )
            queue.append_to_queue("deletion", list(delete_keys_documents))
            storage_with_collection["global_keys"] = list(global_keys_documents)
            storage_with_collection["delete_keys"] = []
            self.local_storage.update_storage(storage_with_collection, "calendar")

        except Exception as exception:
            self.logger.exception(f"Error while deleting the calendars. Error: {exception}")
        self.logger.info("Completed deleting the calendar events from Microsoft Teams")

    def remove_deleted_documents_from_global_keys(
        self, live_documents, list_ids_documents, deleted_documents, global_keys_documents, parent_id, super_parent_id
    ):
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
            self.remove_deleted_documents_from_global_keys(
                live_documents, list_ids_documents, deleted_documents, global_keys_documents, item_id,
                super_parent_id
            )
