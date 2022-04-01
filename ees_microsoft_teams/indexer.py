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
import multiprocessing
import os
from multiprocessing.pool import ThreadPool
from .local_storage import LocalStorage

from iteration_utilities import unique_everseen

from . import constant
from .microsoft_teams_user_messages import MSTeamsUserMessage
from .checkpointing import Checkpoint
from .msal_access_token import MSALAccessToken
from .permission_sync_command import PermissionSyncCommand
from .utils import (get_thread_results, split_date_range_into_chunks,
                    split_list_into_buckets, get_schema_fields, get_records_by_types, is_document_in_present_data)


class Indexer:
    """Indexes the Microsoft Teams objects and its permissions to the Workplace Search.
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
        self.local_storage = LocalStorage(self.logger)

    def bulk_index_documents(self, documents):
        """ Indexes the documents to the Workplace Search
            :param documents: Documents to be indexed into the Workplace Search
        """
        if documents:
            total_records_dict = get_records_by_types(documents)
            for chunk in split_list_into_buckets(documents, constant.BATCH_SIZE):
                response = self.workplace_search_client.index_documents(
                    content_source_id=self.ws_source,
                    documents=chunk
                )
                for each in response['results']:
                    if each['errors']:
                        item = list(filter(lambda seq: is_document_in_present_data(seq, each['id'], "id"), documents))
                        documents.remove(item[0])
                        self.logger.error(f"Error while indexing {each['id']}. Error: {each['errors']}")
            total_inserted_record_dict = get_records_by_types(documents)
            for type, count in total_records_dict.items():
                self.logger.info(f"Total {total_inserted_record_dict[type]} {type} indexed out of {count}.")

    def threaded_index_documents(self, documents, object_type):
        """ Indexes the documents to the Workplace Search using multithreading
            :param documents: Documents to be indexed equally in each thread
            :param object_type: Type of object to be indexed
        """
        self.logger.debug(f"Indexing the {object_type} to the Workplace Search")
        chunk_documents = split_list_into_buckets(documents, self.max_threads)
        thread_pool = ThreadPool(self.max_threads)
        for doc in chunk_documents:
            thread_pool.apply_async(self.bulk_index_documents, (doc, ))

        thread_pool.close()
        thread_pool.join()

    def workplace_add_permission(self, user_name, permissions):
        """ Indexes the user permissions into the Workplace Search
            :param user_name: A string value denoting the Workplace Search username
            :param permissions: Permission that needs to be provided to the user
        """
        try:
            self.workplace_search_client.add_user_permissions(
                content_source_id=self.config.get_value("enterprise_search.source_id"),
                user=user_name,
                body={
                    "permissions": permissions
                },
            )
            self.logger.info(f"Successfully indexed the permissions for user {user_name} to the Workplace Search")
        except Exception as exception:
            self.logger.exception(
                f"Error while indexing the permissions for user {user_name} to the Workplace Search. \
                    Error: {exception}")
            raise exception

    def index_permissions(self, users, permissions):
        """ Maps the Microsoft Teams users to Workplace Search users and indexes the permissions
            for those users
            :param users: Users for indexing the permissions
            :param permissions: User permissions
        """
        rows = {}
        mapping_sheet_path = self.config.get_value("microsoft_teams.user_mapping")
        if (mapping_sheet_path and os.path.exists(mapping_sheet_path) and os.path.getsize(mapping_sheet_path) > 0):
            with open(mapping_sheet_path, encoding="UTF-8") as file:
                csvreader = csv.reader(file)
                for row in csvreader:
                    rows[row[0]] = row[1]
        user_name = rows.get(users, users)
        self.workplace_add_permission(user_name, permissions)

    def index_user_chats(self, user_drive):
        """ Indexes the user chats into the Workplace Search.
            :param user_drive: Dictionary of user drives
        """
        self.logger.debug("Started indexing of user chat, meeting chat, attachments, tabs and meeting recoding")
        storage_with_collection = {"global_keys": [], "delete_keys": []}
        ids_collection = {}
        ids_list = []
        try:
            # Logic to read data from microsoft_teams_user_chat_doc_ids.json file.
            if (os.path.exists(constant.USER_CHAT_DELETION_PATH) and os.path.getsize(
                    constant.USER_CHAT_DELETION_PATH) > 0):
                ids_collection = self.local_storage.load_storage(constant.USER_CHAT_DELETION_PATH)
                ids_collection["global_keys"] = ids_collection.get("global_keys") or []
                ids_list = ids_collection.get("global_keys")
            storage_with_collection["delete_keys"] = copy.deepcopy(ids_collection.get("global_keys"))
            # Logic to get user chat from Microsoft Team based on our last checkpoint.
            user_message_obj = MSTeamsUserMessage(self.access_token, get_schema_fields, self.logger, self.config)
            user_permissions, chats = user_message_obj.get_user_chats(ids_list)

            # Logic to index the permission for user chats
            if self.permission:
                for user_id, mem_dict in user_permissions.items():
                    self.index_permissions(user_id, mem_dict)

            if chats:
                if self.indexing_type == "incremental":
                    start_time, end_time = self.checkpoint.get_checkpoint(
                        constant.CURRENT_TIME, "user_chats")
                else:
                    start_time = self.config.get_value("start_time")
                    end_time = constant.CURRENT_TIME
                # Create partitions of whole timerange based on the maximum threads defined by user in config file
                _, datelist = split_date_range_into_chunks(start_time, end_time, self.max_threads)
                thread_pool = ThreadPool(self.max_threads)
                user_chat_documents, results = [], []
                for num in range(0, self.max_threads):
                    start_time_partition = datelist[num]
                    end_time_partition = datelist[num + 1]
                    # Applying threading on fetching user chat messages
                    chat_thread = thread_pool.apply_async(
                        user_message_obj.get_user_chat_messages, (ids_list, user_drive, chats, start_time_partition,
                                                                  end_time_partition))
                    results.append(chat_thread)

                # Fetches user chat messages from each thread
                user_chats_thread_results = get_thread_results(results)
                user_chat_documents.extend(user_chats_thread_results)

                thread_pool.close()
                thread_pool.join()
                self.threaded_index_documents(list(unique_everseen(user_chat_documents)), constant.USER_CHATS_MESSAGE)

            storage_with_collection["global_keys"] = list(ids_list)
            self.local_storage.update_storage(storage_with_collection, constant.USER_CHAT_DELETION_PATH)
        except Exception as exception:
            self.logger.exception(
                f"Error while indexing user chat, meeting chat, attachments, tabs and meeting recoding. Error: \
                    {exception}")
        self.logger.info("Completed the indexing of user chat, meeting chat, attachments, tabs and meeting recoding")


def init_indexer(indexing_type, config, access_token, workplace_search_client, logger, calendar_token=""):
    """ Manages the multithreading in the Microsoft Teams objects
        :param indexing_type: Type of indexing (full sync or incremental)
        :param config: Configuration values
        :param access_token: Microsoft Teams access token
        :param workplace_search_client: Cached workplace_search client object
        :param logger: Logger object
        :param calendar_token: Access token for accessing the calendar related Graph APIs
    """
    user_drive = multiprocessing.Manager().dict()
    checkpoint = Checkpoint(logger, config)

    indexer = Indexer(access_token, workplace_search_client, indexing_type, config, logger, checkpoint)
    if "user_chats" in config.get_value('objects'):
        indexer.index_user_chats(user_drive)

        logger.debug("Saving the checkpoint for user chats")
        # Setting the checkpoint for User Chats
        _, end_time_chats = checkpoint.get_checkpoint(constant.CURRENT_TIME, "user_chats")
        checkpoint.set_checkpoint(end_time_chats, indexing_type, "user_chats")


def start(indexing_type, config, logger, workplace_search_client):
    """ Starts the execution of the indexing process
        :param indexing_type: The type of the indexing i.e. Incremental Sync or Full sync
        :param config: Configuration object
        :param logger: Cached logger object
        :param workplace_search_client: Cached workplace_search client object
    """
    logger.debug("Started the indexing of Microsoft Teams documents...")
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
    init_indexer(indexing_type, config, token, workplace_search_client, logger, calendar_token=calendar_token)
