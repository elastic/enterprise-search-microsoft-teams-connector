#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
""" This module fetches all the messages, attachments, chat tabs, and meeting
    recordings from Microsoft Teams.
"""
from collections import defaultdict
from . import constant
from .microsoft_teams_client import MSTeamsClient


class MSTeamsUserMessage:
    """Fetches users details from the Microsoft Teams."""

    def __init__(self, access_token, logger, config, local_storage):
        self.token = access_token
        self.client = MSTeamsClient(logger, self.token, config)
        self.logger = logger
        self.is_permission_sync_enabled = config.get_value("enable_document_permission")
        self.config = config
        self.object_type_to_index = config.get_value('object_type_to_index')
        self.local_storage = local_storage

    def get_user_chats(self, ids_list):
        """Fetches user chats by calling '/Chats' api
        :param ids_list: List of ids
        Returns:
            member_dict: List of dictionaries containing chat id and their members
            documents: Documents to be indexed in Workplace Search
        """
        self.logger.debug("Fetching the users chats")
        documents = []
        chat_response_data = self.client.get_user_chats(f"{constant.GRAPH_BASE_URL}/chats?$expand=members")
        if chat_response_data:
            self.logger.info(
                "Fetched the user chat metadata. Attempting to extract the messages from the chats, "
                "attachments and meeting recordings.."
            )
            # member_dict: Dictionary of members with their id for adding permissions
            member_dict = defaultdict(list)
            for chat in chat_response_data:
                for member in chat["members"]:
                    display_name = member["displayName"]
                    if display_name:
                        member_dict[display_name].append(chat["id"])
                # Logic to append chat for deletion
                self.local_storage.insert_document_into_doc_id_storage(
                    ids_list, chat["id"], constant.CHATS, "", ""
                )
                documents.append(chat)
        return member_dict, documents
