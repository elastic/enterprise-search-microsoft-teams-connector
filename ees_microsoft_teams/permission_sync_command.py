#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to synchronize the user permissions from Microsoft Teams to the Workplace Search.
"""

import json
import os

from . import constant


class PermissionSyncCommand:
    """This class contains logic to sync user permissions from Microsoft Teams."""

    def __init__(self, logger, config, workplace_search_client):
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.config = config

    def remove_all_permissions(self):
        """Removes all the permissions present in the Workplace Search
        """
        try:
            cal_ids = []
            if (os.path.exists(constant.CALENDAR_CHAT_DELETION_PATH) and os.path.getsize(
                    constant.CALENDAR_CHAT_DELETION_PATH) > 0):
                with open(constant.CALENDAR_CHAT_DELETION_PATH, encoding="UTF-8") as ids_store:
                    try:
                        indexed_calendars = json.load(ids_store)
                        global_keys_documents = indexed_calendars.get("global_keys", [])
                        type_dict = list(filter(lambda d: d['type'] in 'Calendar', global_keys_documents))
                        cal_ids = list(map(lambda x: x["id"], type_dict))
                    except ValueError as exception:
                        self.logger.exception(
                            f"Error while reading calendars data from the path: \
                                {constant.CALENDAR_CHAT_DELETION_PATH}. Error: {exception}"
                        )
            user_permission = self.workplace_search_client.list_permissions(
                content_source_id=self.config.get_value("enterprise_search.source_id"),
            )

            if user_permission:
                self.logger.debug("Removing the permissions from the Workplace Search...")
                permission_list = user_permission['results']
                for permission in permission_list:
                    permission_ids = list(set(permission['permissions']) - set(cal_ids))
                    self.workplace_search_client.remove_user_permissions(
                        content_source_id=self.config.get_value("enterprise_search.source_id"),
                        user=permission['user'],
                        body={
                            "permissions": permission_ids
                        }
                    )
                self.logger.info("Removed the permissions from the Workplace Search.")
        except Exception as exception:
            self.logger.exception(
                f"Error while removing the permissions from the Workplace Search. Error: {exception}")
            raise exception
