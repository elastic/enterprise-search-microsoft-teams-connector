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
from .utils import extract_api_response, url_encode

USER_CHAT_ATTACHMENT = "User Chat Attachments"


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
