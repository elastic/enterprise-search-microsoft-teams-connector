#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module perform operations related to Enterprise Search based on the Enterprise Search version
"""
from elastic_enterprise_search import WorkplaceSearch, __version__
from packaging import version

ENTERPRISE_V8 = version.parse("8.0")


class EnterpriseSearchWrapper:
    """This class contains operations related to Enterprise Search such as index documents, delete documents, etc."""

    def __init__(self, logger, config, args):
        self.logger = logger
        self.version = version.parse(__version__)
        self.host = config.get_value("enterprise_search.host_url")
        self.api_key = config.get_value("enterprise_search.api_key")
        self.ws_source = config.get_value("enterprise_search.source_id")
        if self.version >= ENTERPRISE_V8:
            if hasattr(args, "user") and args.user:
                self.workplace_search_client = WorkplaceSearch(
                    self.host, basic_auth=(args.user, args.password)
                )
            else:
                self.workplace_search_client = WorkplaceSearch(
                    self.host,
                    bearer_auth=self.api_key,
                )
        else:
            if hasattr(args, "user") and args.user:
                self.workplace_search_client = WorkplaceSearch(
                    f"{self.host}/api/ws/v1/sources",
                    http_auth=(args.user, args.password),
                )
            else:
                self.workplace_search_client = WorkplaceSearch(
                    f"{self.host}/api/ws/v1/sources", http_auth=self.api_key
                )

    def index_documents(self, documents, timeout):
        """Indexes one or more new documents into a custom content source, or updates one
        or more existing documents
        :param documents: list of documents to be indexed
        :param timeout: Timeout in seconds
        """
        try:
            responses = self.workplace_search_client.index_documents(
                content_source_id=self.ws_source,
                documents=documents,
                request_timeout=timeout,
            )
        except Exception as exception:
            self.logger.exception(f"Error while indexing the files. Error: {exception}")
            raise exception
        return responses
