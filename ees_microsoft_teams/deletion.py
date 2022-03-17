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

import os
import json
from datetime import datetime
from .adapter import DEFAULT_SCHEMA
from .microsoft_teams_user_messages import MSTeamsUserMessage
from .microsoft_teams_channels import MSTeamsChannels
from .msal_access_token import MSALAccessToken
from .microsoft_teams_calendars import MSTeamsCalendar
from . import constant
from multiprocessing.pool import ThreadPool
from .utils import split_date_range_into_chunks, get_thread_results
from .checkpointing import Checkpoint


class Deletion:
    """ This class is used to remove document from the workplace search
    """
    def __init__(self, access_token, config, workplace_search_client, logger):
        self.logger = logger
        self.config = config
        self.access_token = access_token
        self.workplace_search_client = workplace_search_client
        self.objects = config.get_value('objects')
        self.max_threads = config.get_value("max_threads")
        self.checkpoint = Checkpoint(logger, config)

    def get_schema_fields(self, document_name):
        """ returns the schema of all the include_fields or exclude_fields specified in the configuration file.
            :param document_name: Document name from Teams, Channels, Channel Messages, User Chats, etc.
            Returns:
                schema: Included and excluded fields schema
        """
        fields = self.objects.get(document_name)
        adapter_schema = DEFAULT_SCHEMA[document_name]
        field_id = adapter_schema['id']
        if fields:
            include_fields = fields.get("include_fields")
            exclude_fields = fields.get("exclude_fields")
            if include_fields:
                adapter_schema = {
                    key: val for key, val in adapter_schema.items() if val in include_fields}
            elif exclude_fields:
                adapter_schema = {
                    key: val for key, val in adapter_schema.items() if val not in exclude_fields}
            adapter_schema['id'] = field_id
        return adapter_schema

    def delete_document(self, final_deleted_list):
        """This method will delete all the documents of specified ids from workplace search
           :param final_deleted_list: list of ids
        """
        for index in range(0, len(final_deleted_list), constant.DOCUMENT_SIZE):
            final_list = final_deleted_list[index:index + constant.DOCUMENT_SIZE]
            try:
                # Logic to delete documents from the workplace search
                self.workplace_search_client.delete_documents(
                    content_source_id=self.config.get_value("enterprise_search.source_id"),
                    document_ids=final_list)
            except Exception as exception:
                self.logger.exception(f"Error while deleting the documents to the workplace. Error: {exception}")
                return []

    def deletion_teams(self):
        """ The purpose of this method is to delete the teams related documents from the workplace search.
        """
        indexed_teams = []
        delete_keys_documents = []
        global_keys_documents = []
        doc_id_data = {"global_keys": [], "delete_keys": []}

        self.logger.info(f"Started deletion process of teams and it's objects on {datetime.now()}")

        if (os.path.exists(constant.CHANNEL_CHAT_DELETION_PATH) and os.path.getsize(constant.CHANNEL_CHAT_DELETION_PATH) > 0):
            with open(constant.CHANNEL_CHAT_DELETION_PATH, encoding="UTF-8") as ids_store:
                try:
                    indexed_teams = json.load(ids_store)
                    indexed_teams["delete_keys"] = indexed_teams.get("delete_keys") or []
                    indexed_teams["global_keys"] = indexed_teams.get("global_keys") or []
                    global_keys_documents = indexed_teams.get("global_keys")
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while reading teams data from the path: {constant.CHANNEL_CHAT_DELETION_PATH}. Error: {exception}"
                    )

                deleted_data = indexed_teams["delete_keys"]

                # Logic to fetch all teams and channel details of microsoft team
                teams_channels_obj = MSTeamsChannels(self.access_token, self.get_schema_fields, self.logger, self.config)
                teams = teams_channels_obj.get_all_teams([])

                # Logic to fetch all channels of Microsoft Teams
                channels, channel_doc = teams_channels_obj.get_team_channels(teams, [])

                thread_documents = {constant.CHANNEL_MESSAGES: [], constant.CHANNEL_DOCUMENTS: [], constant.CHANNEL_TABS: []}
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

                channel_messages_thread_results =  get_thread_results(channel_message_results)
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

                self.iterate_item_ntimes(live_data, deleted_data, delete_keys_documents, global_keys_documents, "", "")
                final_deleted_list = list(delete_keys_documents)
                self.delete_document(final_deleted_list)

                # Logic to update the microsoft_teams_channel_chat_doc_ids.json file with latest data
                doc_id_data["global_keys"] = list(global_keys_documents)
                with open(constant.CHANNEL_CHAT_DELETION_PATH, "w", encoding="UTF-8") as channel_path:
                    try:
                        json.dump(doc_id_data, channel_path, indent=4)
                    except ValueError as exception:
                        self.logger.exception(f'Error while adding ids to json file. Error: {exception}')
        else:
            self.logger.info("No records are present to check for deletion teams and it's objects")
        self.logger.info(f"Completed deletion process of teams and it's objects on {datetime.now()}")


    def deletion_user_chat(self):
        """ The purpose of this method is to delete the user chat related documents from the workplace search.
        """
        indexed_user_chat = []
        delete_keys_documents = []
        global_keys_documents = []
        storage_with_collection = {"global_keys": [], "delete_keys": []}
        self.logger.info(f"Started deletion process of user chat on {datetime.now()}")
        # Logic to read indexed documents from the microsoft_teams_user_chat_doc_ids.json file
        if (os.path.exists(constant.USER_CHAT_DELETION_PATH) and os.path.getsize(constant.USER_CHAT_DELETION_PATH) > 0):
            try:
                with open(constant.USER_CHAT_DELETION_PATH) as ids_store:
                    try:
                        indexed_user_chat = json.load(ids_store)
                        indexed_user_chat["delete_keys"] = indexed_user_chat.get("delete_keys") or []
                        indexed_user_chat["global_keys"] = indexed_user_chat.get("global_keys") or []
                        global_keys_documents = indexed_user_chat.get("global_keys")
                    except ValueError as exception:
                        self.logger.exception(
                            f"Error while reading users chats data from the path: {constant.USER_CHAT_DELETION_PATH}. Error: {exception}"
                        )
                    # Logic to fetch all chats details of microsoft team
                    user_msg = MSTeamsUserMessage(self.access_token, self.get_schema_fields, self.logger, self.config)
                    _, chats = user_msg.get_user_chats([])

                    start_time = self.config.get_value("start_time")
                    end_time = constant.CURRENT_TIME

                    _, datelist = split_date_range_into_chunks(start_time, end_time, self.max_threads)
                    thread_pool = ThreadPool(self.max_threads)
                    user_chat_documents, results = [], []
                    for num in range(0, self.max_threads):
                        start_time_partition = datelist[num]
                        end_time_partition = datelist[num + 1]
                        chat_thread = thread_pool.apply_async(user_msg.get_user_chat_messages, ([], {}, chats, start_time_partition, end_time_partition))
                        results.append(chat_thread)

                    user_chats_thread_results = get_thread_results(results)
                    user_chat_documents.extend(user_chats_thread_results)

                    thread_pool.close()
                    thread_pool.join()

                    docids_data = indexed_user_chat["delete_keys"]
                    # Logic to iterate each items based on parent and child relationship and insert items into global variable for deletion
                    self.iterate_item_ntimes(user_chat_documents, docids_data, delete_keys_documents, global_keys_documents, "", "")
                    final_deleted_list = list(delete_keys_documents)
                    self.delete_document(final_deleted_list)
                    storage_with_collection["global_keys"] = list(global_keys_documents)
                    with open(constant.USER_CHAT_DELETION_PATH, "w") as user_path:
                        try:
                            json.dump(storage_with_collection, user_path, indent=4)
                        except ValueError as exception:
                            self.logger.warn(f'Error while adding ids to json file. Error: {exception}')
            except Exception as exception:
                self.logger.exception(f' Error while deleting user chats details into workplace search. Error: {exception}')
        else:
            self.logger.info("No records are present to check for deletion user chats")
        self.logger.info(f"Completed deletion process of user chat on {datetime.now()}")

    def deletion_calendar_chat(self):
        """ The purpose of this method is to delete the calendar related documents from the workplace search.
        """
        indexed_calendars = []
        delete_keys_documents = []
        global_keys_documents = []
        doc_id_data = {"global_keys": [], "delete_keys": []}

        self.logger.info(f"Started deletion process of calendars on {datetime.now()}")
        if (os.path.exists(constant.CALENDAR_CHAT_DELETION_PATH) and os.path.getsize(constant.CALENDAR_CHAT_DELETION_PATH) > 0):
            with open(constant.CALENDAR_CHAT_DELETION_PATH, encoding="UTF-8") as ids_store:
                try:
                    indexed_calendars = json.load(ids_store)
                    indexed_calendars["delete_keys"] = indexed_calendars.get("delete_keys") or []
                    indexed_calendars["global_keys"] = indexed_calendars.get("global_keys") or []
                    global_keys_documents = indexed_calendars.get("global_keys")
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while reading calendars data from the path: {constant.CALENDAR_CHAT_DELETION_PATH}. Error: {exception}"
                    )

                # Fetching start datetime from them the YML file because we have to we have to fetch all data and check respective document exists or not instead of calling individual to improve performance
                start_time = self.config.get_value("start_time")
                deleted_data = indexed_calendars["delete_keys"]

                # Logic to fetch all chats details of microsoft team
                calendars = MSTeamsCalendar(self.access_token, start_time, constant.CURRENT_TIME, self.get_schema_fields, self.logger, self.config)
                _, documents = calendars.get_calendars([])
                self.iterate_item_ntimes(documents, deleted_data, delete_keys_documents, global_keys_documents, "", "")
                final_deleted_list = list(delete_keys_documents)
                self.delete_document(final_deleted_list)
                # Logic to update the microsoft_teams_user_chat_doc_ids.json file with latest data
                doc_id_data["global_keys"] = list(global_keys_documents)
                with open(constant.CALENDAR_CHAT_DELETION_PATH, "w", encoding="UTF-8") as calendar_path:
                    try:
                        json.dump(doc_id_data, calendar_path, indent=4)
                    except ValueError as exception:
                        self.logger.exception(f'Error while adding ids to json file. Error: {exception}')
        else:
            self.logger.info("No records are present to check for deletion calendars")
        self.logger.info(f"Completed deletion process of calendars on {datetime.now()}")

    def iterate_item_ntimes(self, live_documents, doc_ids_documents, deleted_documents, global_keys_documents, parent_id, super_parent_id):
        """ The purpose of this method is to recursively iterate documents upto N level for deletion.
            :param live_documents: Pass all documents received from user chat
            :param doc_ids_documents: Pass all documents which is availabe inside microsoft_teams_user_chat_doc_ids.json file
            :param deleted_documents: Pass global variable to store deleted documents
            :param global_keys_documents: Pass global variable of global_keys to removed deleted data
            :param parent_id: Pass parent id of first document to start the execution
            :param super_parent_id: Pass super parent id of first document to start the execution
        """
        parent_items = list(filter(lambda seq: self.get_child_items(seq, parent_id), doc_ids_documents))
        for item in parent_items:
            id = item["id"]
            parent_id = item["parent_id"]
            super_parent_id = item["super_parent_id"]
            type = item["type"]
            items_exists = list(filter(
                lambda seq: self.check_item_isexists_in_livedata(seq, id), live_documents))
            if(len(items_exists) == 0 and type not in [constant.CHATS, constant.USER, constant.USER_CHAT_DRIVE, constant.USER_CHAT_DRIVE_ITEM, constant.CHANNEL_DRIVE, constant.CHANNEL_ROOT, constant.CHANNEL_DRIVE_ITEM]):
                deleted_documents.append(id)
                if item in global_keys_documents:
                    global_keys_documents.remove(item)

            # Logic to recursively call same function till the N number of child level.
            self.iterate_item_ntimes(live_documents, doc_ids_documents,
                                     deleted_documents, global_keys_documents, id, super_parent_id)

    def get_child_items(self, document_item, parent_id):
        """ The purpose of this method is to filter child item while iterating each document.
            :param document_item: Pass user chat document
            :param parent_id: Pass parent id of user chat document
        """
        return document_item["parent_id"] == parent_id

    def check_item_isexists_in_livedata(self, document_item, id):
        """ The purpose of this method is to filter item from the live data.
            :param document_item: Pass user chat document
            :param parent_id: Pass id of user chat document
        """
        return document_item["id"] == id


def init_deletion(job_name, access_token, config, workplace_search_client, logger):
    """This function is used for initializing the deletion
       :param job_name: Pass the type of object
       :param access_token: Microsoft Teams access token
       :param config: Configuration object
       :param workplace_search_client: Cached workplace_search client object
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
    """ The purpose of this method is to delete document from the workplace search when it will be deleted from the Microsoft Teams
        and this class run three different process parallelly to delete document from the workplace search. One for User Chat, second for Channel Chat and third for Calendar.
       :param config: Configuration object
       :param logger: Logger object
       :param workplace_search_client: Cached workplace_search client object
    """

    logger.info("Starting the deletion...")
    objects = config.get_value("objects")
    # Logic to generate access token to connect microsoft graph api to fetch data.
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
