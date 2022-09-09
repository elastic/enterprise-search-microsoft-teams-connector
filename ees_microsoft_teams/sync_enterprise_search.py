#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import pandas as pd
from iteration_utilities import unique_everseen

from . import constant
from .utils import (split_documents_into_equal_chunks, split_list_into_buckets, split_documents_into_equal_bytes,
                    is_document_in_present_data)

PERMISSION_LIMIT = 1024


class IndexingError(Exception):
    """Exception raised when indexing gets failed.

    Attributes:
        errors - errors found while indexing the documents to Workplace Search
    """

    def __init__(self, errors):
        super().__init__(f"Error while indexing the documents to Workplace Search. Errors: {errors}.")
        self.errors = errors


class SyncEnterpriseSearch:
    """This class allows ingesting documents to Elastic Enterprise Search."""

    def __init__(self, config, logger, workplace_search_custom_client, queue):
        self.logger = logger
        self.workplace_search_custom_client = workplace_search_custom_client
        self.ws_source = config.get_value("enterprise_search.source_id")
        self.enterprise_search_thread_count = config.get_value(
            "enterprise_search_sync_thread_count"
        )
        self.queue = queue
        self.checkpoint_list = []
        self.permission_list_to_index = []
        self.max_allowed_bytes = 10000000

    def get_records_by_types(self, documents):
        """This method is used to for grouping the document based on their type
        :param documents: Document to be indexed
        Returns:
             df_dict: Dictionary of type with its count
        """
        if not documents:
            return {}
        data_frame = pd.DataFrame(documents)
        data_frame_size = data_frame.groupby("type").size()
        data_frame_dict = data_frame_size.to_dict()
        return data_frame_dict

    def fetch_documents_by_id(self, response, documents):
        """Filters the documents which are getting failed while indexing
        :param response: Response getting from the Workplace Search
        :param documents: Documents to be indexed into the Workplace Search
        """
        return list(filter(lambda seq: is_document_in_present_data(seq, response["id"], "id"), documents,))

    def index_documents(self, documents):
        """This method indexes the documents to the workplace.
        :param documents: Documents to be indexed into the Workplace Search
        """
        if documents:
            total_records_dict = self.get_records_by_types(documents)
            for chunk in split_list_into_buckets(documents, constant.BATCH_SIZE):
                try:
                    response = self.workplace_search_custom_client.index_documents(
                        chunk, constant.CONNECTION_TIMEOUT
                    )
                except IndexingError as exception:
                    raise IndexingError(exception)
                for result in response["results"]:
                    if result["errors"]:
                        failed_document_list = self.fetch_documents_by_id(result, documents)
                        # Removing the failed document from the successfully indexed document count
                        documents = [document for document in documents if document not in failed_document_list]
                        self.logger.error(
                            f"Error while indexing {result['id']}. Error: {result['errors']}"
                        )
            total_inserted_record_dict = self.get_records_by_types(documents)
            for type, count in total_records_dict.items():
                self.logger.info(f"Total {total_inserted_record_dict[type]} {type} indexed out of "
                                 f"{count}." if total_inserted_record_dict else f"Total 0 {type} "
                                 f"indexed out of {count}")

    def workplace_add_permission(self, permission_dict):
        """This method used to index the user permissions into Workplace Search
        for the user in parameter user_name
        :param user_name: A string value denoting the username of the user
        :param permission: Permission that needs to be provided to the user
        """
        try:
            for user_permission in permission_dict:
                user_permissions = split_documents_into_equal_chunks(
                    user_permission["roles"], PERMISSION_LIMIT
                )
                ws_permissions = self.workplace_search_custom_client.list_permissions()
                for permissions in user_permissions:
                    if ws_permissions:
                        permission_lists = ws_permissions["results"]
                        for list_permission in permission_lists:
                            user_name = (
                                list_permission["user"]
                                if "user" in list_permission
                                else list_permission["external_user_properties"][0][
                                    "attribute_value"
                                ]
                            )
                            if user_permission["user"] == user_name:
                                if list_permission["permissions"]:
                                    permissions.extend(list_permission["permissions"])

                    self.workplace_search_custom_client.add_permissions(
                        user_permission["user"],
                        list(set(permissions)),
                    )
                self.logger.info(
                    f"Successfully indexed the permissions for {user_permission['user']} user into the "
                    "Workplace Search"
                )
        except Exception as exception:
            self.logger.exception(
                f"Error while indexing the permissions for user:{user_permission['user']} to the workplace. "
                f"Error: {exception}"
            )
            raise exception

    def perform_sync(self):
        """Pull documents from the queue and synchronize it to the Enterprise Search."""
        signal_open = True
        while signal_open:
            documents_to_index = []
            while (
                    len(documents_to_index) < constant.BATCH_SIZE
                    and len(str(documents_to_index)) < self.max_allowed_bytes
            ):
                documents = self.queue.get()
                if documents.get("type") == "signal_close":
                    signal_open = False
                    break
                elif documents.get("type") == "checkpoint":
                    self.checkpoint_list.append(documents)
                    break
                elif documents.get("type") == "permissions":
                    self.permission_list_to_index.append(documents.get("data"))
                else:
                    documents_to_index.extend(documents.get("data"))
            if documents_to_index:
                documents_to_index = list(unique_everseen(documents_to_index))
                for chunk in split_documents_into_equal_chunks(
                    documents_to_index, constant.BATCH_SIZE
                ):
                    for documents in split_documents_into_equal_bytes(
                        chunk, self.max_allowed_bytes
                    ):
                        self.index_documents(chunk)
            if not signal_open:
                break
