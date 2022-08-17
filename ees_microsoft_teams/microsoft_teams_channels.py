#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module collects all the teams and Channels detail from Microsoft Teams.
"""
import dateparser
import requests
from iteration_utilities import unique_everseen
from requests.exceptions import RequestException
from tika.tika import TikaException

from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import (get_data_from_http_response, get_schema_fields, extract_api_response,
                    html_to_text, url_decode)

MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
CHANNEL_MEETINGS = "Channel Meetings"


class MSTeamsChannels:
    """This class fetches all the teams and channels data from Microsoft Teams.
    """

    def __init__(self, access_token, logger, config, local_storage):
        self.access_token = access_token
        self.client = MSTeamsClient(logger, self.access_token, config)
        self.logger = logger
        self.object_type_to_index = config.get_value('object_type_to_index')
        self.is_permission_sync_enabled = config.get_value("enable_document_permission")
        self.local_storage = local_storage

    def get_all_teams(self, ids_list):
        """ Fetches all the teams from Microsoft Teams
            :param ids_list: Shared storage for storing the document ids
            Returns:
                teams_details: List of dictionaries containing the team details
        """
        self.logger.info("Fetching teams from Microsoft Teams...")
        documents = []
        response = self.client.get_teams(next_url=f"{constant.GRAPH_BASE_URL}/groups")

        if not response:
            return []

        team_schema = get_schema_fields("teams", self.object_type_to_index)
        for team in response:
            team_data = {"type": constant.TEAMS}
            # Logic to append teams for deletion
            self.local_storage.insert_document_into_doc_id_storage(
                ids_list=ids_list, id=team["id"], type=constant.TEAMS
            )

            for workplace_search_field, microsoft_teams_field in team_schema.items():
                team_data[workplace_search_field] = team[microsoft_teams_field]

            if self.is_permission_sync_enabled:
                team_data["_allow_permissions"] = [team["id"]]

            documents.append(team_data)
        return documents

    def get_team_members(self):
        """ Fetches the team members from Microsoft Teams
            Returns:
                member_list: List containing all the team members
        """
        self.logger.info("Fetching team members from Microsoft Teams")

        member_list = {}
        response = self.client.get_teams(next_url=f"{constant.GRAPH_BASE_URL}/groups")

        if not response:
            return member_list

        for team in response:
            self.logger.info(f"Fetching members for the team: {team['displayName']}")
            team_id = team["id"]
            response = self.client.get_teams(
                next_url=f"{constant.GRAPH_BASE_URL}/teams/{team_id}/members"
            )

            if not response:
                return {}

            for member in response:
                display_name = member["displayName"]
                if member_list.get(display_name):
                    member_list[display_name].append(team_id)
                else:
                    member_list[display_name] = [team_id]
        return member_list

    def get_team_channels(self, teams, ids_list):
        """ Fetches all the team channels from the Microsoft Teams
            :param teams: List of dictionaries containing the team details
            :param ids_list: Shared storage for storing the document ids
            Returns:
                documents_with_teams: List of dictionaries containing the team channel details
                documents: Documents to be indexed in Workplace Search
        """
        documents = []
        documents_with_teams = []
        for team in teams:
            team_id = team["id"]
            team_name = team["title"]
            self.logger.info(f"Fetching channels for team: {team_name}")

            response = self.client.get_channels(
                next_url=f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels"
            )

            if not response:
                continue

            channel_schema = get_schema_fields("channels", self.object_type_to_index)
            channels_by_team = {team_id: []}
            for channel in response:
                # Logic to append channels for deletion
                self.local_storage.insert_document_into_doc_id_storage(
                    ids_list, channel["id"], constant.CHANNELS, team_id, ""
                )
                channel_data = {"type": constant.CHANNELS}

                for workplace_search_field, microsoft_teams_field in channel_schema.items():
                    channel_data[workplace_search_field] = channel[microsoft_teams_field]

                if self.is_permission_sync_enabled:
                    channel_data["_allow_permissions"] = [team_id]

                documents.append(channel_data)
                channels_by_team[team_id].append(channel_data)
            documents_with_teams.append(channels_by_team)
        return documents_with_teams, documents

    def get_channel_messages(self, team_channels_list, ids_list, start_time, end_time):
        """ Fetches all the channel messages from the Microsoft Teams
            :param team_channels_list: List of dictionaries containing team_id as a key and
                channels of that team as a value
            :param ids_list: Shared storage for storing the document ids
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            Returns:
                documents: List of dictionaries containing the channel messages details
        """
        self.logger.debug(
            f"Fetching channel messages for the interval of start time: {start_time} and end time: {end_time}.")
        documents = []
        for team_channel_map in team_channels_list:
            for team_id, channel_list in team_channel_map.items():
                for channel in channel_list:
                    channel_id = channel["id"]
                    channel_name = channel["title"]
                    self.logger.info(f"Fetching the channel messages for channel: {channel_name}")

                    response = self.client.get_channel_messages(
                        next_url=f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages",
                        channel_name=channel_name, start_time=start_time, end_time=end_time)

                    if response:
                        documents = self.get_channel_messages_documents(
                            response, channel, ids_list, team_id, start_time, end_time, documents)
        return documents

    def get_channel_messages_documents(
            self, message_response_data, channel, ids_list, team_id, start_time, end_time, documents
    ):
        """Prepares a Workplace Search document for channel messages to be indexed
        :param message_response_data: Response data to prepare a workplace search document
        :param channel: Channel for fetching the channel messages
        :param ids_list: Shared storage for storing the document ids
        :param start_time: Starting time for fetching data
        :param end_time: Ending time for fetching data
        :param documents: Document to be indexed into the Workplace Search
        Returns:
            documents: Document to be indexed into the Workplace Search
        """
        channel_id = channel["id"]
        channel_name = channel["title"]
        channel_message_schema = get_schema_fields("channel_messages", self.object_type_to_index)
        for message in message_response_data:
            message_data = {"type": constant.CHANNEL_MESSAGES}
            if not message["deletedDateTime"]:
                content = html_to_text(self.logger, message["body"]["content"])
                attachments = message.get("attachments")
                is_meeting = message.get("eventDetail") and message.get(
                    "eventDetail", {}).get("callEventType")
                if content or attachments or is_meeting:
                    if content or attachments:
                        self.logger.info("Extracting html/text messages...")
                        sender = message["from"]["user"]["displayName"]
                        attachment_names = self.get_attachment_names(attachments)
                        message_data["title"] = channel_name
                        # If the message has attachments in it, set the message body format to
                        # `sender - attachments`
                        message_data["body"] = f"{sender} - {attachment_names}\n"
                        if content and attachments:
                            # If the message has both content and attachments, set the message
                            # body format to `sender - attachments - message`
                            message_data["body"] += f"Message: {content}\n"
                        elif content:
                            # If the message has just content and no attachments, replace the
                            # message body format with `sender - message`
                            message_data["body"] = f"{sender} - {content}"
                    else:
                        self.logger.info(
                            f"Extracting meeting details for channel: {channel['title']} from "
                            "Microsoft Teams...")
                        message_data["type"] = CHANNEL_MEETINGS
                        meeting_time = message['createdDateTime']
                        formatted_datetime = dateparser.parse(meeting_time).strftime(
                            "%d %b, %Y at %H:%M:%S")
                        message_data["title"] = f"{channel['title']} - Meeting On "\
                                                f"{formatted_datetime}"

                    # Logic to append channel messages for deletion
                    self.local_storage.insert_document_into_doc_id_storage(
                        ids_list, message["id"],
                        constant.CHANNEL_MESSAGES, channel_id, team_id)
                    for workplace_search_field, microsoft_teams_field in channel_message_schema.items():
                        message_data[workplace_search_field] = message[microsoft_teams_field]
                    if self.is_permission_sync_enabled:
                        message_data["_allow_permissions"] = [team_id]
                    replies_data = self.get_message_replies(
                        team_id, channel_id, message['id'], start_time, end_time)
                    if replies_data:
                        if attachments:
                            message_data["body"] += f"Attachment Replies:\n{replies_data}"
                        elif content:
                            message_data["body"] = f"{sender} - {content}\nReplies:\n"\
                                                   f"{replies_data}"
                        else:
                            message_data["body"] = f"Meeting Messages:\n{replies_data}"
                    if message_data:
                        documents.append(message_data)
        return documents

    def get_attachment_names(self, attachments):
        """Convert multiple attachment names into comma separated name
        :param attachments: Attachment object for fetching the attachment names
        Returns:
            attachment_names: List of channel attachments
        """
        attachment_list = []
        for attachment in attachments:
            if attachment["contentType"] == "tabReference":
                attachment["name"] = url_decode(attachment["name"])
            attachment_list.append(attachment["name"])
        attachment_names = ", ".join(attachment_list)
        return attachment_names

    def get_message_replies(self, team_id, channel_id, message_id, start_time, end_time):
        """ Fetches the replies of a specific channel message.
            :param team_id: Team id
            :param channel_id: Channel id
            :param message_id: Parent message id
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            Returns:
                message_body: List of message replies
        """
        self.logger.info(f"Fetching message replies for message id: {message_id}...")
        replies_list = []
        replies_url = f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"

        response = self.client.get_channel_messages(
            next_url=replies_url,
            start_time=start_time,
            end_time=end_time,
            is_message_replies=True
        )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response,
            error_message="Could not fetch the channel message replies.",
            exception_message="Error while fetching the channel message replies."
        )

        if not parsed_response:
            return ""

        for reply in parsed_response:
            reply_content = html_to_text(self.logger, reply["body"]["content"])
            if reply_content:
                sender = reply["from"]["user"]["displayName"]
                replies_list.append(f"{sender} - {reply_content}")

        message_body = "\n".join(reply for reply in replies_list)
        return message_body

    def get_channel_tabs(self, team_channels_list, ids_list, start_time, end_time):
        """ Fetches the channel tabs from the Microsoft Teams.
            :param team_channels_list: List of dictionaries containing team_id as a key and
                channels of that team as a value
            :param ids_list: Shared storage for storing the document ids
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            Returns:
                documents: Documents to be indexed in Workplace Search
        """
        self.logger.debug(
            f"Fetching channel tabs for the interval of start time: {start_time} and end time: {end_time}.")
        documents = []
        tabs_schema = get_schema_fields("channel_tabs", self.object_type_to_index)
        for team_channel_map in team_channels_list:
            for team_id, channel_list in team_channel_map.items():
                for channel in channel_list:
                    channel_id = channel["id"]
                    channel_name = channel['title']
                    self.logger.info(f"Fetching the tabs for channel: {channel_name}")

                    response = self.client.get_channel_tabs(
                        next_url=f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels/{channel_id}/tabs",
                        start_time=start_time,
                        end_time=end_time,
                        channel_name=channel_name
                    )

                    if not response:
                        return documents

                    for tab in response:
                        # Logic to append channel tabs for deletion
                        self.local_storage.insert_document_into_doc_id_storage(
                            ids_list, tab["id"], constant.CHANNEL_TABS, channel_id, team_id)
                        tabs_data = {"type": constant.CHANNEL_TABS}

                        for workplace_search_field, microsoft_teams_field in tabs_schema.items():
                            if workplace_search_field == "title":
                                tabs_data[workplace_search_field] = f"{channel_name}" \
                                                                    f"-{tab[microsoft_teams_field]}"

                            else:
                                tabs_data[workplace_search_field] = tab[microsoft_teams_field]

                        if self.is_permission_sync_enabled:
                            tabs_data["_allow_permissions"] = [team_id]

                        documents.append(tabs_data)
        return documents

    def get_channel_documents(self, teams, ids_list, start_time, end_time):
        """ Fetches all the channel documents from the Microsoft Teams
            :param teams: List of dictionaries containing the team details
            :param ids_list: Shared storage for storing the document ids
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            Returns:
                documents: Documents to be indexed in Workplace Search
        """
        documents = []
        self.logger.debug(
            f"Fetching channel documents for the interval of start time: {start_time} and end time: {end_time}.")

        for team in teams:
            team_id = team["id"]
            team_name = team["title"]
            self.logger.info(f"Fetching drives for team: {team_name}")

            drive_response = self.client.get_channel_drives_and_children(
                next_url=f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives", object_type=constant.DRIVE)

            drive_response_data = get_data_from_http_response(
                self.logger, drive_response,
                f"Could not fetch channels document drives for team:{team_id} Error: {drive_response}",
                f"Error while fetching channels document drives for team: {team_id} Error: {drive_response}")

            if drive_response_data:
                for drive in drive_response_data:
                    drive_id = drive["id"]
                    self.logger.info(f"Fetching root for drive: {drive['name']}")

                    # Logic to append team drives ids for deletion
                    self.local_storage.insert_document_into_doc_id_storage(ids_list, drive_id, constant.CHANNEL_DRIVE,
                                                                           team_id, "")
                    root_response = self.client.get(
                        url=f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives/{drive_id}/root",
                        object_type=constant.ROOT)

                    if root_response:
                        root_id = root_response["id"]
                        self.logger.info(f"Fetching channel drives for root: {root_response['name']}")

                        # Logic to append drive roots ids for deletion
                        self.local_storage.insert_document_into_doc_id_storage(
                            ids_list, root_id, constant.CHANNEL_ROOT, drive_id, team_id)

                        children_response = self.client.get_channel_drives_and_children(
                            next_url=f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives/{drive_id}/items/"
                                     f"{root_id}/children", object_type=constant.DRIVE)

                        children_response_data = get_data_from_http_response(
                            self.logger, children_response,
                            f"Could not fetch channels document drive items for team:{team_id} "
                            f"Error: {children_response}",
                            f"Error while fetching channels document drive items for team: {team_id} "
                            f"Error: {children_response}")

                        if children_response_data:
                            document_schema = get_schema_fields("channel_documents", self.object_type_to_index)

                            for child in children_response_data:
                                # Logic to append drive item ids for deletion
                                self.local_storage.insert_document_into_doc_id_storage(
                                    ids_list, child["id"], constant.CHANNEL_DRIVE_ITEM, root_id, drive_id)

                                folder_documents = self.get_folder_documents(
                                    team_id, drive_id, child["id"],
                                    document_schema, [],
                                    ids_list, child["id"],
                                    start_time, end_time, team_name)

                                if folder_documents:
                                    documents.extend(folder_documents)
        return list(unique_everseen(documents))

    def get_folder_documents(
            self, team_id, drive_id, document_id, schema, documents, ids_list, parent_file_id, start_time,
            end_time, team_name):
        """ Fetches the files from the folder recursively
            :param team_id: Team id
            :param drive_id: Drive id
            :param document_id: Folder id
            :param schema: Schema for workplace fields and Microsoft Teams fields
            :param documents: Document id storage
            :param ids_list: Shared storage for storing the document ids
            :param parent_file_id: Parent document id of current file/folder
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            :param team_name: Team name for log message
            Returns:
                documents: list of documents containing the channel documents details
        """
        folder_files_url = f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives/{drive_id}/items/{document_id}/children"
        folder_files_response = self.client.get_channel_documents(
            next_url=folder_files_url, start_time=start_time, end_time=end_time,
            object_type=constant.CHANNEL_DOCUMENTS, team_name=team_name)

        if not folder_files_response:
            return documents

        for document in folder_files_response:
            # Logic to append recursive files/folders for deletion
            self.local_storage.insert_document_into_doc_id_storage(
                ids_list, document["id"], constant.CHANNEL_DOCUMENTS, document_id, parent_file_id)
            document_data = {"type": constant.CHANNEL_DOCUMENTS}

            if document.get("folder") and type(document.get("folder")) != float:
                self.get_folder_documents(
                    team_id, drive_id, document["id"],
                    schema, documents, ids_list, document_id, start_time, end_time, team_name)

            for workplace_search_field, microsoft_teams_filed in schema.items():
                document_data[workplace_search_field] = document[microsoft_teams_filed]

            document_data["_allow_permissions"] = []
            if self.is_permission_sync_enabled:
                document_data["_allow_permissions"] = [team_id]

            document_data["body"] = self.get_attachment_content(document)
            documents.append(document_data)
        return documents

    def get_attachment_content(self, document):
        """ This function is used to fetch and extract the channel document from download URL
            :param document: document that contains the details of channel document
            Returns:
                attachment_content: content of the attachment
        """
        is_file = document.get("file", {})

        # validate if file is exractable and not null
        if is_file and type(is_file) != float:
            mimetype = is_file.get("mimeType")

            if mimetype not in constant.MIMETYPES:
                download_url = document.get("@microsoft.graph.downloadUrl")
                try:
                    attachment_content_response = requests.get(download_url)
                    if attachment_content_response:
                        attachment_content = None
                        try:
                            self.logger.info(f"Extracting the contents of {document.get('name')}.")
                            attachment_content = extract_api_response(attachment_content_response.content)
                        except TikaException as exception:
                            self.logger.exception(
                                f"Error while extracting contents of {document['name']} via Tika Parser. Error: "
                                f"{exception}")
                        return attachment_content
                except RequestException as exception:
                    self.logger.exception(
                        f"Error while downloading the channel document from download URL: {download_url}. Error: "
                        f"{exception}")
                    raise exception
