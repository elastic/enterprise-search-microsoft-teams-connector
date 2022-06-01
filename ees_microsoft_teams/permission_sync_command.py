#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to synchronize the user permissions from Microsoft Teams to the Workplace Search.
"""


class PermissionSyncCommand:
    """This class contains logic to sync user permissions from Microsoft Teams."""

    def __init__(self, logger, config, workplace_search_client):
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.config = config
        self.enterprise_search_source_id = self.config.get_value("enterprise_search.source_id")

    def list_user_permissions(self):
        """ Returns the list of users permissions from Workplace Search
        """
        self.logger.debug("Fetching the user permissions from the workplace search")
        user_permission = self.workplace_search_client.list_permissions(
            content_source_id=self.enterprise_search_source_id,
        )
        user_permissions_dict = {}
        for user_dict in user_permission['results']:
            user_permissions_dict.update({user_dict["user"]: user_dict["permissions"]})
        return user_permissions_dict
