# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import os
import json
from src import constant
from src.base_class import BaseClass


class UserGroupPermissions(BaseClass):
    def __init__(self, logger):
        BaseClass.__init__(self, logger=logger)
        self.logger = logger

    def remove_all_permissions(self):
        """ Removes all the permissions present in the workplace
        """
        try:
            if (os.path.exists(constant.CALENDAR_CHAT_DEINDEXING_PATH) and os.path.getsize(constant.CALENDAR_CHAT_DEINDEXING_PATH) > 0):
                with open(constant.CALENDAR_CHAT_DEINDEXING_PATH, encoding="UTF-8") as ids_store:
                    try:
                        indexed_calendars = json.load(ids_store)
                        global_keys_documents = indexed_calendars.get("global_keys", [])
                        type_dict = list(filter(lambda d: d['type'] in 'Calendar', global_keys_documents))
                        cal_ids = list(map(lambda x: x["id"], type_dict))
                    except ValueError as exception:
                        self.logger.exception(
                            "Error while reading calendars data from the path: %s. Error: %s"
                            % (constant.CALENDAR_CHAT_DEINDEXING_PATH, exception)
                        )
            user_permission = self.ws_client.list_permissions(
                content_source_id=self.ws_source,
                http_auth=self.ws_token,
            )

            if user_permission:
                self.logger.info("Removing the permissions from the workplace...")
                permission_list = user_permission['results']
                for permission in permission_list:
                    permission_ids = list(set(permission['permissions']) - set(cal_ids))
                    self.ws_client.remove_user_permissions(
                        content_source_id=self.ws_source,
                        http_auth=self.ws_token,
                        user=permission['user'],
                        body={
                            "permissions": permission_ids
                        }
                    )
                self.logger.info("Successfully removed the permissions from the workplace.")
        except Exception as exception:
            self.logger.exception(f"Error while removing the permissions from the workplace. Error: {exception}")
