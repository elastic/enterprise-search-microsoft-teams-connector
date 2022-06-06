#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import pandas as pd
from elastic_enterprise_search import BadGatewayError, InternalServerError
from iteration_utilities import unique_everseen

from . import constant
from .utils import split_documents_into_equal_chunks, split_list_into_buckets

PERMISSION_LIMIT = 1024


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

    def get_records_by_types(self, documents):
        """This method is used to for grouping the document based on their type
        :param documents: Document to be indexed
        Returns:
             df_dict: Dictionary of type with its count
        """
        if not documents:
            return {}
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
                except InternalServerError:
                    raise InternalServerError("Error while indexing the documents due to Internal Server error.")
                except BadGatewayError:
                    raise BadGatewayError("Error while indexing the documents due to Bad Gateway error.")
                except Exception as exception:
                    raise Exception(f"Error while indexing the documents. Error: {exception}")
                for each in response["results"]:
                    if each["errors"]:
                        item = list(
                            filter(
                                lambda seq: self.filter_removed_item_by_id(
                                    seq, each["id"]
                                ),
                                documents,
                            )
                        )
                        documents.remove(item[0])
                        self.logger.error(
                            f"Error while indexing {each['id']}. Error: {each['errors']}"
                        )
            total_inserted_record_dict = self.get_records_by_types(documents)
            for type, count in total_records_dict.items():
                self.logger.info(f"Total {total_inserted_record_dict[type]} {type} indexed out of "
                                 f"{count}." if total_inserted_record_dict else f"Total 0 {type} "
                                 f"indexed out of {count}")

    def perform_sync(self):
        """Pull documents from the queue and synchronize it to the Enterprise Search."""
        signal_open = True
        while signal_open:
            for _ in range(0, self.enterprise_search_thread_count):
                documents_to_index = []
                while len(documents_to_index) < constant.BATCH_SIZE:
                    documents = self.queue.get()
                    if documents.get("type") == "signal_close":
                        signal_open = False
                        break
                    elif documents.get("type") == "checkpoint":
                        self.checkpoint_list.append(documents.get("data"))
                        break
                    else:
                        documents_to_index.extend(documents.get("data"))
                if documents_to_index:
                    documents_to_index = list(unique_everseen(documents_to_index))
                    for chunk in split_documents_into_equal_chunks(
                        documents_to_index, constant.BATCH_SIZE
                    ):
                        self.index_documents(chunk)
                if not signal_open:
                    break
