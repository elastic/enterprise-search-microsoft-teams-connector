#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
""" This module fetches all the messages, attachments, chat tabs, and meeting
    recordings from Microsoft Teams.
"""
import requests

from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import (extract_api_response, get_schema_fields, html_to_text,
                    url_encode)

USER_CHAT_ATTACHMENT = "User Chat Attachments"
MEETING_RECORDING = "Meeting Recording"
USER_CHAT_TABS = "User Chat Tabs"


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

    def get_user_chat_messages(
        self,
        ids_list,
        user_drive,
        chat_response_data,
        start_time,
        end_time,
        user_attachment_token,
    ):
        """Fetches the user chat messages from Microsoft Teams
        :param ids_list: List of ids
        :param user_drive: Dictionary of dictionary
        :param chat_response_data: Chats data for fetching chat messages
        :param start_time: Starting time for fetching data
        :param end_time: Ending time for fetching data
        :param user_attachment_token: Access token for fetching the attachments
        Returns:
            documents: Documents to be indexed in Workplace Search
        """
        documents = []
        user_schema = get_schema_fields("user_chats", self.object_type_to_index)
        attachment_client = MSTeamsClient(
            self.logger, user_attachment_token, self.config
        )
        for val in chat_response_data:
            member_title = []
            for member in val["members"]:
                display_name = member["displayName"]
                if display_name:
                    member_title.append(display_name)
            # Logic to append chat for deletion
            try:
                chat_detail_response = self.client.get_user_chat_messages(
                    f'{constant.GRAPH_BASE_URL}/chats/{val["id"]}/messages',
                    start_time,
                    end_time,
                    val['id']
                )
                if chat_detail_response:
                    for chat in chat_detail_response:
                        if not chat["deletedDateTime"]:
                            title = (
                                val.get("topic")
                                if val.get("topic")
                                else ",".join(member_title)
                            )
                            sender = chat["from"]
                            user_name = ""
                            if sender and sender["user"]:
                                user_id = sender.get("user", {}).get("id")
                                user_name = sender.get("user", {}).get("displayName")
                                for attachment in chat["attachments"]:
                                    name = attachment["name"]
                                    if name and attachment["contentType"] == "reference":
                                        attachment_document = self.get_attachments(
                                            user_id,
                                            title,
                                            name,
                                            attachment["id"],
                                            val["id"],
                                            chat["lastModifiedDateTime"],
                                            ids_list,
                                            user_drive,
                                            attachment_client
                                        )
                                        if attachment_document:
                                            documents.extend(attachment_document)
                            content = chat["body"]["content"]
                            chat_message = html_to_text(self.logger, content)
                            if chat_message:
                                # Logic to append chat message for deletion
                                self.local_storage.insert_document_into_doc_id_storage(
                                    ids_list,
                                    chat["id"],
                                    constant.USER_CHATS_MESSAGE,
                                    val["id"],
                                    "",
                                )
                                user_dict = {"type": constant.USER_CHATS_MESSAGE}
                                for ws_field, ms_fields in user_schema.items():
                                    user_dict[ws_field] = chat[ms_fields]
                                user_dict["title"] = title
                                user_dict["body"] = (
                                    f"{user_name} - {chat_message}" if user_name else chat_message
                                )
                                user_dict["url"] = val["webUrl"]

                                user_dict["_allow_permissions"] = []
                                if self.is_permission_sync_enabled:
                                    user_dict["_allow_permissions"] = [val["id"]]
                                documents.append(user_dict)
                            else:
                                self.logger.info(
                                    f"the message for the chat {chat['id']} is empty"
                                )
                            meeting_recordings = self.fetch_meeting_recording(
                                val["id"], chat
                            )
                            if meeting_recordings:
                                documents.append(meeting_recordings)
            except Exception as exception:
                self.logger.exception(
                    f"[Fail] Error while fetching user chats details from teams. Error: {exception}"
                )
                raise exception
            self.logger.info(
                f"Fetched chats, attachments and meeting recordings metadata. Attempting to fetch tabs "
                f"for chat: {val['id']}"
            )
            tabs_document = self.fetch_tabs(val["id"], ids_list, start_time, end_time)
            documents.extend(tabs_document)
            self.logger.info("Fetched the user chat tabs")
        return documents
