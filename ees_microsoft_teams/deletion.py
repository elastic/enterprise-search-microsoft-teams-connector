#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in Microsoft Teams will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""

import json
import os
from datetime import datetime
from multiprocessing.pool import ThreadPool

from . import constant
from .checkpointing import Checkpoint
from .microsoft_teams_calendars import MSTeamsCalendar
from .microsoft_teams_channels import MSTeamsChannels
from .microsoft_teams_user_messages import MSTeamsUserMessage
from .msal_access_token import MSALAccessToken
from .local_storage import LocalStorage
from .utils import get_thread_results, split_date_range_into_chunks, get_schema_fields, is_document_in_present_data


class Deletion:
    """Removes the documents from the Workplace Search.
    """

    def __init__(self, access_token, config, workplace_search_client, logger):
        self.logger = logger
        self.config = config
        self.access_token = access_token
        self.workplace_search_client = workplace_search_client
        self.objects = config.get_value('objects')
        self.max_threads = config.get_value("max_threads")
        self.checkpoint = Checkpoint(logger, config)
        self.local_storage = LocalStorage(self.logger)

    def delete_documents(self, final_deleted_list):
        """Deletes the documents of specified ids from Workplace Search
           :param final_deleted_list: List of ids to delete the documents from Workplace Search
        """
        for index in range(0, len(final_deleted_list), constant.BATCH_SIZE):
            final_list = final_deleted_list[index:index + constant.BATCH_SIZE]
            try:
                # Logic to delete documents from the workplace search
                self.workplace_search_client.delete_documents(
                    content_source_id=self.config.get_value("enterprise_search.source_id"),
                    document_ids=final_list)
            except Exception as exception:
                self.logger.exception(
                    f"Error while deleting the documents to the Workplace Search. Error: {exception}")
                return []

    def deletion_teams(self):
        """Deletes the teams related documents from the Workplace Search.
        """
        indexed_teams = []
        delete_keys_documents = []
        global_keys_documents = []
        list_ids_data = {"global_keys": [], "delete_keys": []}

        self.logger.debug(f"Started the deletion process of teams and it's objects on {datetime.now()}")

        if (os.path.exists(constant.CHANNEL_CHAT_DELETION_PATH) and os.path.getsize(
                constant.CHANNEL_CHAT_DELETION_PATH) > 0):
            indexed_teams = self.local_storage.load_storage(constant.CHANNEL_CHAT_DELETION_PATH)
            indexed_teams["delete_keys"] = indexed_teams.get("delete_keys") or []
            indexed_teams["global_keys"] = indexed_teams.get("global_keys") or []
            global_keys_documents = indexed_teams.get("global_keys")

            deleted_data = indexed_teams.get("delete_keys")

            # Logic to fetch all teams and channel details of microsoft team
            teams_channels_obj = MSTeamsChannels(self.access_token, get_schema_fields, self.logger,
                                                 self.config)
            teams = teams_channels_obj.get_all_teams([])

            # Logic to fetch all channels of Microsoft Teams
            channels, channel_doc = teams_channels_obj.get_team_channels(teams, [])

            thread_documents = {constant.CHANNEL_MESSAGES: [], constant.CHANNEL_DOCUMENTS: [],
                                constant.CHANNEL_TABS: []}
            channel_message_results, channel_tab_results, channel_documents_results = [], [], []
            thread_pool = ThreadPool(self.max_threads)
            start_time = self.config.get_value("start_time")
            end_time = constant.CURRENT_TIME

            _, datelist = split_date_range_into_chunks(start_time, end_time, self.max_threads)
            for num in range(0, self.max_threads):
                start_time_partition = datelist[num]
                end_time_partition = datelist[num + 1]

                # Applying threading on fetching channel messages
                message_thread = thread_pool.apply_async(teams_channels_obj.get_channel_messages,
                                                         (channels, [], start_time_partition, end_time_partition))
                channel_message_results.append(message_thread)

                # Applying threading on fetching channel tabs
                tabs_thread = thread_pool.apply_async(teams_channels_obj.get_channel_tabs,
                                                      (channels, [], start_time_partition, end_time_partition))
                channel_tab_results.append(tabs_thread)

                # Applying threading on fetching channel documents
                documents_thread = thread_pool.apply_async(teams_channels_obj.get_channel_documents,
                                                           (teams, [], start_time_partition, end_time_partition))
                channel_documents_results.append(documents_thread)

            channel_messages_thread_results = get_thread_results(channel_message_results)
            thread_documents[constant.CHANNEL_MESSAGES].extend(channel_messages_thread_results)

            # Fetches channel tabs from each thread
            channel_tabs_thread_results = get_thread_results(channel_tab_results)
            thread_documents[constant.CHANNEL_TABS].extend(channel_tabs_thread_results)

            # Fetches channel documents from each thread
            channel_documents_thread_results = get_thread_results(channel_documents_results)
            thread_documents[constant.CHANNEL_DOCUMENTS].extend(channel_documents_thread_results)

            thread_pool.close()
            thread_pool.join()

            live_data = []
            live_data.extend(teams)
            live_data.extend(channel_doc)
            live_data.extend(thread_documents[constant.CHANNEL_MESSAGES])
            live_data.extend(thread_documents[constant.CHANNEL_TABS])
            live_data.extend(thread_documents[constant.CHANNEL_DOCUMENTS])

            self.update_local_storage(live_data, deleted_data, delete_keys_documents, global_keys_documents, "", "")
            final_deleted_list = list(delete_keys_documents)
            self.delete_documents(final_deleted_list)

            # Logic to update the microsoft_teams_channel_chat_doc_ids.json file with latest data
            list_ids_data["global_keys"] = list(global_keys_documents)
            self.local_storage.update_storage(list_ids_data, constant.CHANNEL_CHAT_DELETION_PATH)
        else:
            self.logger.debug("No records found for the deletion of teams and it's objects")
        self.logger.info(f"Completed the deletion of teams and it's objects on {datetime.now()}")

    def deletion_user_chat(self):
        """ Deletes the user chats related documents from the Workplace Search.
        """
        indexed_user_chat = []
        delete_keys_documents = []
        global_keys_documents = []
        list_ids_data = {"global_keys": [], "delete_keys": []}
        self.logger.debug(f"Started the deletion process of user chats on {datetime.now()}")
        # Logic to read indexed documents from the microsoft_teams_user_chat_doc_ids.json file
        if (os.path.exists(constant.USER_CHAT_DELETION_PATH) and os.path.getsize(
                constant.USER_CHAT_DELETION_PATH) > 0):
            try:
                indexed_user_chat = self.local_storage.load_storage(constant.USER_CHAT_DELETION_PATH)
                indexed_user_chat["delete_keys"] = indexed_user_chat.get("delete_keys") or []
                indexed_user_chat["global_keys"] = indexed_user_chat.get("global_keys") or []
                global_keys_documents = indexed_user_chat.get("global_keys")

                # Logic to fetch all chats details of microsoft team
                user_message_obj = MSTeamsUserMessage(self.access_token, get_schema_fields, self.logger, self.config)
                _, chats = user_message_obj.get_user_chats([])

                start_time = self.config.get_value("start_time")
                end_time = constant.CURRENT_TIME

                _, datelist = split_date_range_into_chunks(start_time, end_time, self.max_threads)
                thread_pool = ThreadPool(self.max_threads)
                user_chat_documents, results = [], []
                for num in range(0, self.max_threads):
                    start_time_partition = datelist[num]
                    end_time_partition = datelist[num + 1]
                    chat_thread = thread_pool.apply_async(user_message_obj.get_user_chat_messages, (
                        [], {}, chats, start_time_partition, end_time_partition))
                    results.append(chat_thread)

                user_chats_thread_results = get_thread_results(results)
                user_chat_documents.extend(user_chats_thread_results)

                thread_pool.close()
                thread_pool.join()

                list_ids_data = indexed_user_chat.get("delete_keys")
                # Logic to iterate each items based on parent and child relationship and insert items into global
                # variable for deletion
                self.update_local_storage(user_chat_documents, list_ids_data, delete_keys_documents,
                                          global_keys_documents, "", "")
                final_deleted_list = list(delete_keys_documents)
                self.delete_documents(final_deleted_list)
                list_ids_data["global_keys"] = list(global_keys_documents)
                self.local_storage.update_storage(list_ids_data, constant.USER_CHAT_DELETION_PATH)
            except Exception as exception:
                self.logger.exception(f' Error while deleting user chats details into workplace search. Error: \
                    {exception}')
        else:
            self.logger.debug("No records found for the deletion of user chats")
        self.logger.info(f"Completed the deletion process of user chat on {datetime.now()}")

    def deletion_calendar_chat(self):
        """ Deletes the calendar related documents from the Workplace Search.
        """
        indexed_calendars = []
        delete_keys_documents = []
        global_keys_documents = []
        list_ids_data = {"global_keys": [], "delete_keys": []}

        self.logger.debug(f"Started deletion process of calendars on {datetime.now()}")
        if (os.path.exists(constant.CALENDAR_CHAT_DELETION_PATH) and os.path.getsize(
                constant.CALENDAR_CHAT_DELETION_PATH) > 0):
            indexed_calendars = self.local_storage.load_storage(constant.CALENDAR_CHAT_DELETION_PATH)
            indexed_calendars["delete_keys"] = indexed_calendars.get("delete_keys") or []
            indexed_calendars["global_keys"] = indexed_calendars.get("global_keys") or []
            global_keys_documents = indexed_calendars.get("global_keys")

            # Fetching start datetime from them the YML file because we have to we have to fetch all data and
            # check respective document exists or not instead of calling individual to improve performance
            start_time = self.config.get_value("start_time")
            deleted_data = indexed_calendars.get("delete_keys")

            # Logic to fetch all chats details of microsoft team
            calendars = MSTeamsCalendar(self.access_token, start_time, constant.CURRENT_TIME,
                                        get_schema_fields, self.logger, self.config)
            _, documents = calendars.get_calendars([])
            self.update_local_storage(documents, deleted_data, delete_keys_documents, global_keys_documents, "", "")
            final_deleted_list = list(delete_keys_documents)
            self.delete_documents(final_deleted_list)
            # Logic to update the microsoft_teams_user_chat_doc_ids.json file with latest data
            list_ids_data["global_keys"] = list(global_keys_documents)
            self.local_storage.update_storage(list_ids_data, constant.CALENDAR_CHAT_DELETION_PATH)
        else:
            self.logger.debug("No records found for the deletion of calendars")
        self.logger.info(f"Completed the deletion process of calendars on {datetime.now()}")

    def update_local_storage(self, live_documents, list_ids_documents, deleted_documents, global_keys_documents,
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
            self.update_local_storage(live_documents, list_ids_documents,
                                      deleted_documents, global_keys_documents, item_id, super_parent_id)


def init_deletion(job_name, access_token, config, workplace_search_client, logger):
    """Initializes the deletion process
       :param job_name: Type of the object to delete the documents
       :param access_token: Access Token for accessing the Graph APIs
       :param config: Configuration object
       :param workplace_search_client: Cached Workplace Search client object
       :param logger: Logger object
    """
    deletion = Deletion(access_token, config, workplace_search_client, logger)
    if job_name == "teams":
        deletion.deletion_teams()
    if job_name == "user_chats":
        deletion.deletion_user_chat()
    if job_name == "calendar":
        deletion.deletion_calendar_chat()


def start(config, logger, workplace_search_client):
    """ Starts the execution of the deletion process to delete the documents from the Workplace Search.
       :param config: Configuration object
       :param logger: Logger object
       :param workplace_search_client: Cached workplace_search client object
    """
    logger.debug("Starting the execution of deletion process...")
    objects = config.get_value("objects")
    token = MSALAccessToken(logger, config)
    obj_permissions_list = ["teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]
    access_token = token.get_token()
    if any(obj in objects for obj in obj_permissions_list):
        init_deletion("teams", access_token, config, workplace_search_client, logger)
    if "user_chats" in objects:
        init_deletion("user_chats", access_token, config, workplace_search_client, logger)
    if "calendar" in objects:
        calendar_access_token = token.get_token(is_acquire_for_client=True)
        init_deletion("calendar", calendar_access_token, config, workplace_search_client, logger)
