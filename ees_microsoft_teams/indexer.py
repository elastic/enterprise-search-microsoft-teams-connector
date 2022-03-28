#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to sync data to Elastic Enterprise Search.

    It's possible to run full syncs and incremental syncs with this module.
"""

import copy
import csv
import json
import os
from multiprocessing.pool import ThreadPool

import pandas as pd
from iteration_utilities import unique_everseen

from . import constant
from .adapter import DEFAULT_SCHEMA
from .checkpointing import Checkpoint
from .microsoft_teams_channels import MSTeamsChannels
from .msal_access_token import MSALAccessToken
from .permission_sync_command import PermissionSyncCommand
from .utils import (get_thread_results, split_date_range_into_chunks,
                    split_list_into_buckets)


class Indexer:
    """ This class is responsible for indexing the Microsoft Teams objects and it's permissions to the Workplace Search.
    """

    def __init__(self, access_token, workplace_search_client, indexing_type, config, logger, checkpoint):
        self.logger = logger
        self.config = config
        self.access_token = access_token
        self.workplace_search_client = workplace_search_client
        self.objects = config.get_value('objects')
        self.permission = config.get_value("enable_document_permission")
        self.max_threads = config.get_value("max_threads")
        self.ws_source = config.get_value("enterprise_search.source_id")
        self.checkpoint = checkpoint
        self.indexing_type = indexing_type

    def get_schema_fields(self, document_name):
        """ Returns the schema of all the include_fields or exclude_fields specified in the configuration file.
            :param document_name: Document name from teams, channels, channel_messages, channel_tabs,
                channel_documents, calendar and user_chats
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
                adapter_schema = {key: val for key, val in adapter_schema.items() if val in include_fields}
            elif exclude_fields:
                adapter_schema = {key: val for key, val in adapter_schema.items() if val not in exclude_fields}
            adapter_schema['id'] = field_id
        return adapter_schema

    def get_records_by_types(self, document):
        """This method is used to for grouping the document based on their type
           :param document: Document to be indexed
           Returns:
                df_dict: Dictionary of type with its count
        """
        df = pd.DataFrame(document)
        df_size = df.groupby('type').size()
        df_dict = df_size.to_dict()
        return df_dict

    def filter_removed_item_by_id(self, item, id):
        """This method is used filter removed document by id
           :param item: Pass document
           :param id: Pass id of the document which having error from workplace search
        """
        return item["id"] == id

    def bulk_index_documents(self, documents):
        """ This method indexes the documents to the workplace.
            :param documents: Documents to be indexed into the Workplace Search
        """
        if documents:
            total_records_dict = self.get_records_by_types(documents)
            for chunk in split_list_into_buckets(documents, constant.BATCH_SIZE):
                response = self.workplace_search_client.index_documents(
                    content_source_id=self.ws_source,
                    documents=chunk
                )
                for each in response['results']:
                    if each['errors']:
                        item = list(filter(lambda seq: self.filter_removed_item_by_id(seq, each['id']), documents))
                        documents.remove(item[0])
                        self.logger.error(f"Error while indexing {each['id']}. Error: {each['errors']}")
            total_inserted_record_dict = self.get_records_by_types(documents)
            for type, count in total_records_dict.items():
                self.logger.info(f"Total {total_inserted_record_dict[type]} {type} indexed out of {count}.")

    def threaded_index_documents(self, documents, object_type):
        """ This method is used to index the documents to the Workplace
            Search using multithreading
            :param documents: Documents to be indexed equally in each thread
            :param object_type: Type of object to be indexed
        """
        self.logger.info(f"Indexing the {object_type} to the Workplace Search")
        chunk_documents = split_list_into_buckets(documents, self.max_threads)
        thread_pool = ThreadPool(self.max_threads)
        for doc in chunk_documents:
            thread_pool.apply_async(self.bulk_index_documents, (doc, ))

        thread_pool.close()
        thread_pool.join()

    def workplace_add_permission(self, user_name, permissions):
        """ This method used to index the user permissions into Workplace Search
            for the user in parameter user_name
            :param user_name: A string value denoting the username of the user
            :param permission: Permission that needs to be provided to the user
        """
        try:
            self.workplace_search_client.add_user_permissions(
                content_source_id=self.config.get_value("enterprise_search.source_id"),
                user=user_name,
                body={
                    "permissions": permissions
                },
            )
            self.logger.info(f"Successfully indexed the permissions for user {user_name} to the workplace")
        except Exception as exception:
            self.logger.exception(
                f"Error while indexing the permissions for user:{user_name} to the workplace. Error: {exception}")
            raise exception

    def index_permissions(self, user, roles):
        """ This method is used to map the Microsoft Teams users to workplace search
            users and responsible to call the user permissions indexer method
            :param users: Users for indexing the permissions
            :param roles: User roles
        """
        rows = {}
        mapping_sheet_path = self.config.get_value("msteams_workplace_user_mapping")
        if (mapping_sheet_path and os.path.exists(mapping_sheet_path) and os.path.getsize(mapping_sheet_path) > 0):
            with open(mapping_sheet_path, encoding="UTF-8") as file:
                csvreader = csv.reader(file)
                for row in csvreader:
                    rows[row[0]] = row[1]
        user_name = rows.get(user, user)
        self.workplace_add_permission(user_name, roles)

    def index_teams_and_children(self, teams_channels_obj):
        """ This method is used to index teams, channels and it's objects data
            :param teams_channels_obj: Microsoft Teams channels objects
        """
        self.logger.info("Start fetching and indexing the teams and it's objects data...")
        storage_with_collection = {"global_keys": [], "delete_keys": []}
        ids_collection = {}
        ids_list = []

        try:
            # Logic to read data from microsoft_teams_channel_chat_doc_ids.json file.
            if (os.path.exists(constant.CHANNEL_CHAT_DELETION_PATH) and os.path.getsize(
                    constant.CHANNEL_CHAT_DELETION_PATH) > 0):
                with open(constant.CHANNEL_CHAT_DELETION_PATH, encoding="UTF-8") as ids_store:
                    try:
                        ids_collection = json.load(ids_store)
                        ids_collection["global_keys"] = ids_collection.get("global_keys") or []
                        ids_list = ids_collection.get("global_keys")
                    except ValueError as exception:
                        self.logger.exception(
                            f"Error while parsing the json file of the ids store from path: \
                                {constant.CHANNEL_CHAT_DELETION_PATH}. Error: {exception}"
                        )
            storage_with_collection["delete_keys"] = copy.deepcopy(
                ids_collection.get("global_keys"))

            is_exists_channel_message = "channel_messages" in self.objects
            is_exists_channel_tabs = "channel_tabs" in self.objects
            is_exists_channel_documents = "channel_documents" in self.objects
            if self.indexing_type == "incremental":
                start_time, end_time = self.checkpoint.get_checkpoint(
                    constant.CURRENT_TIME, "teams")
            else:
                start_time = self.config.get_value("start_time")
                end_time = constant.CURRENT_TIME

            # Get teams and its objects from Microsoft Teams and index them
            # into workplace search.
            teams = teams_channels_obj.get_all_teams(ids_list)
            if "teams" in self.objects:
                self.threaded_index_documents(teams, constant.TEAMS)

            # Get channels from Microsoft Teams and index them into
            # workplace search.
            if teams:
                channels, documents = teams_channels_obj.get_team_channels(teams, ids_list)
                if "channels" in self.objects:
                    self.threaded_index_documents(documents, constant.CHANNELS)

                if channels:
                    thread_documents = {constant.CHANNEL_MESSAGES: [],
                                        constant.CHANNEL_DOCUMENTS: [], constant.CHANNEL_TABS: []}
                    channel_message_results, channel_tab_results, channel_documents_results = [], [], []
                    _, datelist = split_date_range_into_chunks(start_time, end_time, self.max_threads)

                    thread_pool = ThreadPool(self.max_threads)
                    for num in range(0, self.max_threads):
                        start_time_partition = datelist[num]
                        end_time_partition = datelist[num + 1]

                        # Applying threading on fetching channel messages
                        if is_exists_channel_message:
                            message_thread = thread_pool.apply_async(
                                teams_channels_obj.get_channel_messages,
                                (channels, ids_list, start_time_partition, end_time_partition))
                            channel_message_results.append(message_thread)

                        # Applying threading on fetching channel tabs
                        if is_exists_channel_tabs:
                            tabs_thread = thread_pool.apply_async(
                                teams_channels_obj.get_channel_tabs,
                                (channels, ids_list, start_time_partition, end_time_partition))
                            channel_tab_results.append(tabs_thread)

                        # Applying threading on fetching channel documents
                        if is_exists_channel_documents:
                            documents_thread = thread_pool.apply_async(
                                teams_channels_obj.get_channel_documents,
                                (teams, ids_list, start_time_partition, end_time_partition))
                            channel_documents_results.append(documents_thread)

                        # Fetches channel messages from each thread
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

                    if is_exists_channel_message:
                        self.threaded_index_documents(list(unique_everseen(
                            thread_documents[constant.CHANNEL_MESSAGES])), constant.CHANNEL_MESSAGES)
                    if is_exists_channel_tabs:
                        self.threaded_index_documents(list(unique_everseen(
                            thread_documents[constant.CHANNEL_TABS])), constant.CHANNEL_TABS)
                    if is_exists_channel_documents:
                        self.threaded_index_documents(list(unique_everseen(
                            thread_documents[constant.CHANNEL_DOCUMENTS])), constant.CHANNEL_DOCUMENTS)

            storage_with_collection["global_keys"] = list(ids_list)
            with open(constant.CHANNEL_CHAT_DELETION_PATH, "w", encoding="UTF-8") as f:
                try:
                    json.dump(storage_with_collection, f, indent=4)
                except ValueError as exception:
                    self.logger.warn(f'Error while adding document ids to json file. Error: {exception}')
        except Exception as exception:
            self.logger.exception(f"Error while indexing the teams or it's objects data. Error: {exception}")
        self.logger.info("Completed indexing teams and it's objects data to the Workplace Search")

    def index_teams_channels(self):
        """ This method is responsible for indexing teams and channel objects
        """
        teams_channels_obj = MSTeamsChannels(self.access_token, self.get_schema_fields, self.logger, self.config)
        if any(obj in self.objects for obj in [
                "teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]):
            if self.permission:
                members_list = teams_channels_obj.get_team_members()
                for member, team_id_list in members_list.items():
                    self.index_permissions(member, team_id_list)
            self.index_teams_and_children(teams_channels_obj)


def init_indexing(indexing_type, config, access_token, workplace_search_client, logger, calendar_token=""):
    """ This method manages the multithreading in the Microsoft Teams objects
        :param indexing_type: Type of indexing (full sync or incremental)
        :param config: Configuration values
        :param access_token: Microsoft Teams access token
        :param workplace_search_client: Cached workplace_search client object
        :param logger: Logger object
        :param calendar_token: Microsoft Teams calendar access token
    """
    obj_permissions_list = ["teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]
    checkpoint = Checkpoint(logger, config)

    indexer = Indexer(access_token, workplace_search_client, indexing_type, config, logger, checkpoint)
    if any(obj in config.get_value('objects') for obj in obj_permissions_list):
        indexer.index_teams_channels()

    logger.info("Saving the checkpoints")
    # Setting the checkpoint for Teams
    _, end_time_teams = checkpoint.get_checkpoint(constant.CURRENT_TIME, "teams")
    checkpoint.set_checkpoint(end_time_teams, indexing_type, "teams")


def start(indexing_type, config, logger, workplace_search_client):
    """ Runs the indexing logic regularly after a given interval
        or puts the connector to sleep
        :param indexing_type: The type of the indexing i.e. Incremental Sync or Full sync
        :param config: Configuration object
        :param logger: Cached logger object
        :param workplace_search_client: Cached workplace_search client object
    """
    logger.info("Starting the indexing...")
    calendar_token = ""
    if config.get_value("enable_document_permission"):
        PermissionSyncCommand(logger, config, workplace_search_client).remove_all_permissions()
    docids_dir = os.path.dirname(constant.USER_CHAT_DELETION_PATH)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(docids_dir):
        os.makedirs(docids_dir)
    token = MSALAccessToken(logger, config)
    if "calendar" in config.get_value("objects"):
        calendar_token = token.get_token(is_acquire_for_client=True)
    token = token.get_token()
    init_indexing(indexing_type, config, token, workplace_search_client, logger, calendar_token=calendar_token)
