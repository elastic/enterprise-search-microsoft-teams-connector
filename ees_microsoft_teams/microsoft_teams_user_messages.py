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
from .utils import (check_response, extract_api_response, html_to_text,
                    insert_document_into_doc_id_storage, url_encode)

MEETING_RECORDING = "Meeting Recording"


class MSTeamsUserMessage:
    """Fetches users details from the Microsoft Teams."""

    def __init__(self, access_token, get_schema_fields, logger, config):
        self.token = access_token
        self.client = MSTeamsClient(logger, self.token, config)
        self.get_schema_fields = get_schema_fields
        self.logger = logger
        self.permission = config.get_value("enable_document_permission")
        self.config = config
        self.objects = config.get_value("objects")

    def fetch_meeting_recording(self, chat_id, chat):
        """Fetches meeting recording from the Microsoft Teams
        :param chat_id: Id of the chat
        :param chat: dictionary of the user chat
        Returns: recording_dict: Document to be indexed in Workplace Search
        """
        if (
            chat["eventDetail"] and chat["eventDetail"][
                "@odata.type"] == "#microsoft.graph.callRecordingEventMessageDetail"
        ):
            url = chat["eventDetail"].get("callRecordingUrl")
            if url and ".sharepoint.com" in url:
                recording_dict = {"type": MEETING_RECORDING}
                recording_dict["id"] = chat["eventDetail"]["callId"]
                recording_dict["title"] = chat["eventDetail"][
                    "callRecordingDisplayName"
                ]
                recording_dict["url"] = url
                if self.permission:
                    recording_dict["_allow_permissions"] = [chat_id]
                return recording_dict

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
        user_schema = self.get_schema_fields("user_chats", self.objects)
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
                chat_detail = self.client.get(
                    f'{constant.GRAPH_BASE_URL}/chats/{val["id"]}/messages',
                    constant.USER_CHATS_MESSAGE,
                    True,
                    False,
                    page_size=50,
                    filter_query=f"{start_time}/{end_time}",
                )
                chat_detail_response = check_response(
                    self.logger,
                    chat_detail,
                    f"Could not fetch user chats messages for chat id: {val['id']}",
                    "[Fail] Error while fetching user chats details from teams for chat id: {val['id']}.",
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
                                user_name = sender.get("user", {}).get("displayName")
                            content = chat["body"]["content"]
                            msg = html_to_text(self.logger, content)
                            if msg:
                                # Logic to append chat message for deletion
                                insert_document_into_doc_id_storage(
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
                                    f"{user_name} - {msg}" if user_name else msg
                                )
                                user_dict["url"] = val["webUrl"]
                                if self.permission:
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
        return documents
