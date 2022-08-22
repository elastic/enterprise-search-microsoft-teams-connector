#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
""" This module fetches all the messages, attachments, chat tabs, and meeting
    recordings from Microsoft Teams.
"""
from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import get_schema_fields

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
            raise exception

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
