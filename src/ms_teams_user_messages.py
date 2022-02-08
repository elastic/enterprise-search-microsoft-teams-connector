# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import requests
from src.base_class import BaseClass
from src.utils import print_and_log, html_to_text, check_response, insert_document_into_doc_id_storage, extract_api_response
from src.ms_teams_client import MSTeamsClient
from src.msal_access_token import MSALAccessToken
from src import constant


class MSTeamsUserMessage(BaseClass):
    """ This class fetches all users, user messages and user attachments
        from the MS Teams and indexes to the Workplace Search.
    """

    def __init__(self, access_token, start_time, end_time, get_schema_fields, logger):
        BaseClass.__init__(self, logger=logger,
                           access_token=access_token)
        self.token = access_token
        self.client = MSTeamsClient(self.logger, self.token)
        self.is_error = False
        self.start_time = start_time
        self.end_time = end_time
        self.get_schema_fields = get_schema_fields

    def get_attachments(self, user_id, prefix, attachment_name, attachment_id, chat_id, updated_date, doc_ids_storage, user_drive, attachment_client):
        """This method fetch all the attachments of a user
           :param user_id: Id of the user
           :param prefix: Title of the chat message
           :param attachment_name: Name of the attachment
           :param attachment_id: Id of the attachment
           :param chat_id: Id of chat
           :param updated_date: date of chat updated
           :param doc_ids_storage: List of ids
           :param user_drive: dictonary of user id with drive id
           Returns: att_list: Documents to be indexed in Workplace Search
        """
        try:
            item_id = None
            # Checking the userid in user_drive dictonary for saving the else iteration.If userid present in the dict so we'll use its drive id .
            if user_drive.get(user_id):
                drive_id = list(user_drive[user_id].keys())[0]
            else:
                user_drive_response = attachment_client.get(f'{constant.GRAPH_BASE_URL}/users/{user_id}/drive', constant.ATTACHMENTS, False, False, filter_query="/")
                if user_drive_response:
                    user_drive_response_data = user_drive_response.json()
                    # Logic to append user for deindexing
                    insert_document_into_doc_id_storage(doc_ids_storage, user_id, constant.USER, "", "")
                    if user_drive_response_data:
                        drive_id = user_drive_response_data["id"]
                        user_drive[user_id] = {drive_id: None}
                        # Logic to append user drive for deindexing
                        insert_document_into_doc_id_storage(doc_ids_storage, drive_id, constant.USER_CHAT_DRIVE, user_id, "")
            if user_drive:
                # Check that item_id is present with the drive id or not for saving the else itearation.
                if user_drive.get(user_id).get(drive_id):
                    item_id = user_drive.get(user_id).get(drive_id)
                else:
                    users_root_response = attachment_client.get(f'{constant.GRAPH_BASE_URL}/drives/{drive_id}/items/root/children', constant.ATTACHMENTS, False, False, filter_query="/")
                    user_root_response_data, _ = check_response(self.logger, users_root_response.json(), f"Could not fetch the root user for the drive: {drive_id}", f"Error while fetching the root users for drive: {drive_id}")
                    if user_root_response_data:
                        for child in user_root_response_data:
                            if child['name'] == 'Microsoft Teams Chat Files':
                                item_id = child['id']
                                user_drive[user_id][drive_id] = item_id
                                break
            att_list = []
            if item_id:
                # Logic to append user drive item for deindexing
                insert_document_into_doc_id_storage(doc_ids_storage, item_id, constant.USER_CHAT_DRIVE_ITEM, drive_id, user_id)
                final_attachment_url = f"{constant.GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/children?$filter=name eq '{attachment_name}'"
                attachment_response = attachment_client.get(final_attachment_url, constant.ATTACHMENTS, False, False, filter_query="/")
                attachment_response_data, _ = check_response(self.logger, attachment_response.json(), f"Could not fetch the child items for the drive item:{item_id}", f"Error while fetching the child items for drive item:{item_id}")
                document = attachment_response_data[0]
                att_dict = {"type": constant.USER_CHAT_ATTACHMENT}
                is_file = document.get("file", {})
                if is_file and type(is_file) != float:
                    mimetype = is_file.get("mimeType")
                    if mimetype not in constant.MIMETYPES:
                        attachment_content_response = requests.get(document.get("@microsoft.graph.downloadUrl"))
                        if attachment_content_response:
                            attachment_content = extract_api_response(attachment_content_response.content)
                            att_dict["id"] = attachment_id
                            att_dict["title"] = f"{prefix}-{attachment_name}"
                            att_dict["body"] = attachment_content if attachment_content else ''
                            att_dict["url"] = document.get("webUrl")
                            att_dict["last_updated"] = updated_date
                            if self.permission:
                                att_dict["_allow_permissions"] = [chat_id]
                            att_list.append(att_dict)
                            # Logic to append user chat attachment for deindexing
                            insert_document_into_doc_id_storage(doc_ids_storage, attachment_id, constant.USER_CHAT_ATTACHMENT, item_id, drive_id)
            return att_list
        except Exception as exception:
            print_and_log(
                self.logger,
                "exception",
                "[Fail] Error while fetching attachments for user chats. Error: %s"
                % (
                    exception
                ),
            )

    def fetch_tabs(self, chat_id, doc_ids_storage):
        """This method fetch all tabs from the chat
           :param chat_id: Id of the chat
           :param doc_ids_storage: List of ids
           Returns: document: Documents to be indexed in Workplace Search
        """
        try:
            document = []
            tab_response = self.client.get(f'{constant.GRAPH_BASE_URL}/chats/{chat_id}/tabs', constant.USER_CHAT_TABS, False, False, is_pandas_series=True, filter_query=f'{self.start_time}/{self.end_time}', datetime_filter_column_name="dateAdded")
            tab_detail_response, self.is_error = check_response(self.logger, tab_response, f"Could not fetch user tabs for chat id: {chat_id}", f"[Fail] Error while fetching user tabs from teams for chat id: {chat_id}.")
            if tab_detail_response:
                tab_schema = self.get_schema_fields("user_tabs")
                for tab in tab_detail_response:
                    tab_dict = {"type": constant.USER_CHAT_TABS}
                    for ws_field, ms_fields in tab_schema.items():
                        tab_dict[ws_field] = tab[ms_fields]
                    tab_dict['url'] = tab['configuration']['websiteUrl']
                    if self.permission:
                        tab_dict["_allow_permissions"] = [chat_id]
                    document.append(tab_dict)
                    insert_document_into_doc_id_storage(doc_ids_storage, tab['id'], constant.USER_CHAT_TABS, chat_id, "")
            return document
        except Exception as exception:
            print_and_log(
                self.logger,
                "exception",
                "[Fail] Error while fetching user tabs from teams. Error: %s"
                % (
                    exception,
                ),
            )

    def fetch_meeting_recording(self, chat_id, chat):
        """This method fetches all the meeting recordings from the chat
           :param chat_id: Id of the chat
           :param chat: dictonary of chat
           Returns: document: Documents to be indexed in Workplace Search
        """
        if chat['eventDetail'] and chat['eventDetail']['@odata.type'] == '#microsoft.graph.callRecordingEventMessageDetail':
            url = chat['eventDetail'].get('callRecordingUrl')
            if url and ".sharepoint.com" in url:
                recording_dict = {"type": constant.MEETING_RECORDING}
                recording_dict['id'] = chat['eventDetail']['callId']
                recording_dict['title'] = chat['eventDetail']['callRecordingDisplayName']
                recording_dict['url'] = url
                if self.permission:
                    recording_dict["_allow_permissions"] = [chat_id]
                return recording_dict

    def get_chats(self, doc_ids_storage, user_drive):
        """ This methods fetch chats,tabs, attachment and meeting recordings by calling '/Chats' api
            :param doc_ids_storage: List of ids
            :param user_drive: dictonary of dictonary
            Returns: member_dict: List of dictonaries containing chat id and their members
                     document: Documents to be indexed in Workplace Search
                     self.is_error: Boolean value
        """
        self.logger.info("Fetching users chats")
        document = []
        user_schema = self.get_schema_fields("user_chats")
        try:
            chat_response = self.client.get(
                f'{constant.GRAPH_BASE_URL}/chats?$expand=members', constant.CHATS, True, False, page_size=50, filter_query='/')
            chat_response_data, self.is_error = check_response(
                self.logger, chat_response, "Could not fetch user chats", "[Fail] Error while fetching user chats from teams")
        except Exception as exception:
            print_and_log(
                self.logger,
                "exception",
                "[Fail] Error while fetching user chats from teams. Error: %s"
                % (
                    exception,
                ),
            )
        if chat_response_data:
            self.logger.info("Fetched the user chat metadata. Attempting to extract the messages from the chats, attachments and meeting recordings..")
            # member_dict: dictory of members with their id for adding permissions
            member_dict = {}
            user_attachment_token = MSALAccessToken(self.logger)
            user_attachment_token = user_attachment_token.get_token(is_aquire_for_client=True)
            attachment_client = MSTeamsClient(self.logger, user_attachment_token)
            for val in chat_response_data:
                member_title = []
                for member in val['members']:
                    display_name = member['displayName']
                    if display_name:
                        member_dict[display_name] = [*member_dict.get(display_name, []) + [val['id']]]
                        member_title.append(display_name)
                # Logic to append chat for deindexing
                insert_document_into_doc_id_storage(doc_ids_storage, val['id'], constant.CHATS, "", "")
                try:
                    chat_detail = self.client.get(
                        f'{constant.GRAPH_BASE_URL}/chats/{val["id"]}/messages', constant.USER_CHATS_MESSAGE, True, False, page_size=50, filter_query=f'{self.start_time}/{self.end_time}')
                    chat_detail_response, self.is_error = check_response(
                        self.logger, chat_detail, f"Could not fetch user chats messages for chat id: {val['id']}", "[Fail] Error while fetching user chats details from teams for chat id: {val['id']}.")
                    if chat_detail_response:
                        for chat in chat_detail_response:
                            if not chat['deletedDateTime']:
                                title = val.get('topic') if val.get('topic') else ','.join(member_title)
                                # Logic to append chat message for deindexing
                                insert_document_into_doc_id_storage(doc_ids_storage, chat['id'], constant.USER_CHATS_MESSAGE, val['id'], "")
                                sender = chat['from']
                                user_name = ""
                                if sender and sender['user']:
                                    user_id = sender.get("user", {}).get("id")
                                    user_name = sender.get("user", {}).get("displayName")
                                    for att in chat['attachments']:
                                        name = att['name']
                                        if name and att['contentType'] == "reference":
                                            attachment = self.get_attachments(user_id, title, name, att['id'], val["id"], chat['lastModifiedDateTime'], doc_ids_storage, user_drive, attachment_client)
                                            document.extend(attachment)
                                content = chat['body']['content']
                                msg = html_to_text(self.logger, content)
                                if msg:
                                    user_dict = {"type": constant.USER_CHATS_MESSAGE}
                                    for ws_field, ms_fields in user_schema.items():
                                        user_dict[ws_field] = chat[ms_fields]
                                    user_dict['title'] = title
                                    user_dict['body'] = f"{user_name} - {msg}" if user_name else msg
                                    user_dict['url'] = val['webUrl']
                                    if self.permission:
                                        user_dict["_allow_permissions"] = [val['id']]
                                    document.append(user_dict)
                                else:
                                    self.logger.info(f"the message for the chat {chat['id']} is empty")
                                meeting_rec = self.fetch_meeting_recording(val['id'], chat)
                                if meeting_rec:
                                    document.append(meeting_rec)
                except Exception as exception:
                    print_and_log(
                        self.logger,
                        "exception",
                        "[Fail] Error while fetching user chats details from teams. Error: %s"
                        % (
                            exception,
                        ),
                    )
                self.logger.info(f"fetched chats, attachments and meeting recordings metadata.Attempting to fetch tabs for chat:{val['id']}")
                tabs_document = self.fetch_tabs(val['id'], doc_ids_storage)
                document.extend(tabs_document)
                self.logger.info("fetched the user tabs")
        return member_dict, document, self.is_error
