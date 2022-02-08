# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

from src.configuration import Configuration
from elastic_enterprise_search import WorkplaceSearch


class BaseClass(object):
    """ This is the base class for initializing most frequently used assets.
    """
    def __init__(self, **kwargs):
        self.logger = kwargs.get("logger")
        config = Configuration(self.logger)
        self.configurations = config.configurations
        self.username = self.configurations["username"]
        self.password = self.configurations["password"]
        self.tenant_id = self.configurations["tenant_id"]
        self.client_id = self.configurations["application_id"]
        self.client_secret = self.configurations["client_secret"]
        self.retry_count = int(self.configurations.get("retry_count"))
        self.mapping_sheet_path = self.configurations.get("msteams_workplace_user_mapping")
        self.ws_host = self.configurations.get("enterprise_search.host_url")
        self.ws_token = self.configurations.get("enterprise_search.access_token")
        self.ws_source = self.configurations.get("enterprise_search.source_id")
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)
        self.permission = self.configurations.get("enable_document_permission")
        self.objects = self.configurations.get("objects")


if __name__ == "__main__":
    BaseClass()
