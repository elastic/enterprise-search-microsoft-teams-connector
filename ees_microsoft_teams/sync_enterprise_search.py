#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import pandas as pd
from iteration_utilities import unique_everseen

from . import constant
from .checkpointing import Checkpoint
from .utils import split_documents_into_equal_chunks, split_list_into_buckets


class SyncEnterpriseSearch:
    """This class allows ingesting documents to Elastic Enterprise Search."""

    def __init__(self, config, logger, workplace_search_client, queue):
        self.config = config
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.ws_source = config.get_value("enterprise_search.source_id")
        self.enterprise_search_thread_count = config.get_value(
            "enterprise_search_sync_thread_count"
        )
        self.queue = queue

    def get_records_by_types(self, documents):
        """This method is used to for grouping the document based on their type
        :param documents: Document to be indexed
        Returns:
             df_dict: Dictionary of type with its count
        """
        df = pd.DataFrame(documents)
        df_size = df.groupby("type").size()
        df_dict = df_size.to_dict()
        return df_dict

    def filter_removed_item_by_id(self, item, id):
        """This method is used filter removed document by id
        :param item: Pass document
        :param id: Pass id of the document which having error from workplace search
        """
        return item["id"] == id

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

    def perform_sync(self):
        """Pull documents from the queue and synchronize it to the Enterprise Search."""
        checkpoint = Checkpoint(self.logger, self.config)
        signal_open = True
        while signal_open:
            for _ in range(0, self.enterprise_search_thread_count):
                documents_to_index, permission_documents, deleted_document = [], [], []
                while len(documents_to_index) < constant.BATCH_SIZE:
                    documents = self.queue.get()
                    if documents.get("type") == "signal_close":
                        signal_open = False
                        break
                    elif documents.get("type") == "checkpoint":
                        checkpoint.set_checkpoint(
                            documents.get("data")[0],
                            documents.get("data")[1],
                            documents.get("data")[2],
                        )
                        break
                    elif documents.get("type") == "permissions":
                        permission_documents.append(documents.get("data"))
                    elif documents.get("type") == "deletion":
                        deleted_document.extend(documents.get("data"))
                    else:
                        documents_to_index.extend(documents.get("data"))
                if deleted_document:
                    deleted_document = list(unique_everseen(deleted_document))
                    for chunk in split_documents_into_equal_chunks(deleted_document, constant.BATCH_SIZE):
                        self.delete_documents(chunk)
                if not signal_open:
                    break
