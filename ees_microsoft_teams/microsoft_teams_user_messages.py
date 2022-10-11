#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
""" This module fetches all the messages, attachments, chat tabs, and meeting
    recordings from Microsoft Teams.
"""
from collections import defaultdict
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

    def get_attachments(
        self,
        user_id,
        prefix,
        attachment_name,
        attachment_id,
        chat_id,
        updated_date,
        ids_list,
        user_drive,
        attachment_client
    ):
        """Fetches all the attachments of a user chat
        :param user_id: Id of the user
        :param prefix: Title of the chat message
        :param attachment_name: Name of the attachment
        :param attachment_id: Id of the attachment
        :param chat_id: Id of chat
        :param updated_date: date of chat updated
        :param ids_list: List of ids
        :param user_drive: Dictionary of user id with drive id
        :param attachment_client: Object of Microsoft team client
        Returns:
            attachment_list: Documents to be indexed in Workplace Search
        """
        try:
            item_id = None

            # Checking if the user_id is present in user_drive dictionary for saving the else iteration. If user_id is
            # present in the dictionary then we'll directly use its drive_id for fetching attachments.
            if user_drive.get(user_id):
                drive_id = list(user_drive[user_id].keys())[0]

            else:
                user_drive_response = attachment_client.get_user_chat_attachment_drive(
                    f"{constant.GRAPH_BASE_URL}/users/{user_id}/drive"
                )

                if user_drive_response:
                    # Logic to append user for deletion
                    self.local_storage.insert_document_into_doc_id_storage(
                        ids_list, user_id, constant.USER, "", ""
                    )
                    drive_id = user_drive_response["id"]
                    user_drive[user_id] = {drive_id: None}

                    # Logic to append user drive for deletion
                    self.local_storage.insert_document_into_doc_id_storage(
                        ids_list, drive_id, constant.USER_CHAT_DRIVE, user_id, ""
                    )

            if user_drive:
                # Check that item_id is present with the drive id or not for saving the else iteration.
                if user_drive.get(user_id).get(drive_id):
                    item_id = user_drive.get(user_id).get(drive_id)

                else:
                    user_root_response_data = attachment_client.get_user_chat_attachment_drive_children(
                        f"{constant.GRAPH_BASE_URL}/drives/{drive_id}/items/root/children"
                    )

                    if user_root_response_data:
                        for child in user_root_response_data:
                            if child["name"] == "Microsoft Teams Chat Files":
                                item_id = child["id"]
                                user_drive[user_id][drive_id] = item_id
                                break

            attachment_list = []
            if not item_id:
                return []

            # Logic to append user drive item for deletion
            self.local_storage.insert_document_into_doc_id_storage(
                ids_list, item_id, constant.USER_CHAT_DRIVE_ITEM, drive_id, user_id
            )
            final_attachment_url = f"{constant.GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/children?" \
                f"$filter=name eq '{url_encode(attachment_name)}'"
            attachment_response_data = attachment_client.get_user_chat_attachment_drive_children(
                final_attachment_url)

            if attachment_response_data:
                document = attachment_response_data[0]
                attachment_dict = {"type": USER_CHAT_ATTACHMENT}
                is_file = document.get("file", {})

                if is_file and type(is_file) != float:
                    mimetype = is_file.get("mimeType")

                    if mimetype not in constant.MIMETYPES:
                        attachment_content_response = requests.get(
                            document.get("@microsoft.graph.downloadUrl")
                        )

                        if attachment_content_response:
                            attachment_content = extract_api_response(
                                attachment_content_response.content
                            )

                            attachment_dict["id"] = attachment_id
                            attachment_dict["title"] = f"{prefix}-{attachment_name}"
                            attachment_dict["body"] = attachment_content or ""
                            attachment_dict["url"] = document.get("webUrl")
                            attachment_dict["last_updated"] = updated_date
                            attachment_dict["_allow_permissions"] = []
                            if self.is_permission_sync_enabled:
                                attachment_dict["_allow_permissions"] = [chat_id]

                            attachment_list.append(attachment_dict)
                            # Logic to append user chat attachment for deletion
                            self.local_storage.insert_document_into_doc_id_storage(
                                ids_list,
                                attachment_id,
                                USER_CHAT_ATTACHMENT,
                                item_id,
                                drive_id,
                            )
            return attachment_list
        except Exception as exception:
            self.logger.exception(
                f"[Fail] Error while fetching attachments for the user chats. Error: {exception}"
            )

    def fetch_tabs(self, chat_id, ids_list, start_time, end_time):
        """Fetches user chat tabs from the Microsoft Teams
        :param chat_id: Id of the chat
        :param ids_list: List of ids
        :param start_time: Starting time for fetching data
        :param end_time: Ending time for fetching data
        Returns:
            documents: Documents to be indexed in Workplace Search
        """
        try:
            documents = []
            tab_detail_response = self.client.get_user_chat_tabs(
                f"{constant.GRAPH_BASE_URL}/chats/{chat_id}/tabs",
                start_time, end_time, chat_id
            )

            if tab_detail_response:
                tab_schema = get_schema_fields("user_tabs", self.object_type_to_index)
                for tab in tab_detail_response:
                    tab_dict = {"type": USER_CHAT_TABS}
                    for ws_field, ms_fields in tab_schema.items():
                        tab_dict[ws_field] = tab[ms_fields]
                    tab_dict["url"] = tab["configuration"]["websiteUrl"]

                    tab_dict["_allow_permissions"] = []
                    if self.is_permission_sync_enabled:
                        tab_dict["_allow_permissions"] = [chat_id]
                    documents.append(tab_dict)
                    self.local_storage.insert_document_into_doc_id_storage(
                        ids_list, tab["id"], USER_CHAT_TABS, chat_id, ""
                    )
            return documents
        except Exception as exception:
            self.logger.exception(
                f"[Fail] Error while fetching user tabs from teams. Error: {exception}"
            )
            raise

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

                recording_dict["_allow_permissions"] = []
                if self.is_permission_sync_enabled:
                    recording_dict["_allow_permissions"] = [chat_id]
                return recording_dict

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
                raise
            self.logger.info(
                f"Fetched chats, attachments and meeting recordings metadata. Attempting to fetch tabs "
                f"for chat: {val['id']}"
            )
            tabs_document = self.fetch_tabs(val["id"], ids_list, start_time, end_time)
            documents.extend(tabs_document)
            self.logger.info("Fetched the user chat tabs")
        return documents
