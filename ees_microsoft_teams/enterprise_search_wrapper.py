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

    def create_content_source(self, schema, display, name, is_searchable):
        """Create a content source
        :param schema: schema of the content source
        :param display: display schema for the content source
        :param name: name of the content source
        :param is_searchable: boolean to indicate source is searchable or not
        """
        try:
            if self.version >= ENTERPRISE_V8:
                response = self.workplace_search_client.create_content_source(
                    name=name,
                    schema=schema,
                    display=display,
                    is_searchable=is_searchable,
                )
            else:
                body = {
                    "name": name,
                    "schema": schema,
                    "display": display,
                    "is_searchable": is_searchable,
                }
                response = self.workplace_search_client.create_content_source(body=body)
            content_source_id = response.get("id")
            self.logger.info(
                f"Created ContentSource with ID {content_source_id}. \
                    You may now begin indexing with content-source-id= {content_source_id}"
            )
        except Exception as exception:
            self.logger.error(f"Could not create a content source, Error {exception}")
