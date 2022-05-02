#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module collects all the teams and Channels detail from Microsoft Teams.
"""
from json import JSONDecodeError

import dateparser  # noqa
import requests
from iteration_utilities import unique_everseen
from requests.exceptions import RequestException
from tika.tika import TikaException

from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import (check_response, extract_api_response, html_to_text,
                    insert_document_into_doc_id_storage, url_decode)

MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
CHANNEL_MEETINGS = "Channel Meetings"


class MSTeamsChannels:
    """This class fetches all the teams and channels data from Microsoft Teams.
    """

    def __init__(self, access_token, get_schema_fields, logger, config):
        self.access_token = access_token
        self.client = MSTeamsClient(logger, self.access_token, config)
        self.get_schema_fields = get_schema_fields
        self.logger = logger
        self.objects = config.get_value('objects')
        self.permission = config.get_value("enable_document_permission")

    def get_all_teams(self, ids_list):
        """ Fetches all the teams from Microsoft Teams
            :param ids_list: Shared storage for storing the document ids
            Returns:
                teams_details: List of dictionaries containing the team details
        """
        documents = []
        teams_url = f"{constant.GRAPH_BASE_URL}/groups"
        self.logger.info("Fetching the teams from Microsoft Teams...")
        team_response = self.client.get(teams_url, constant.TEAMS, True, False, page_size=999, filter_query="/")
        team_response_data = check_response(
            self.logger, team_response, "Could not fetch the teams from Microsoft Teams",
            "Error while fetching the teams from Microsoft Teams")
        if team_response_data:
            team_schema = self.get_schema_fields("teams", self.objects)
            for team in team_response_data:
                # Logic to append teams for deletion
                insert_document_into_doc_id_storage(ids_list, team["id"], constant.TEAMS, "", "")
                team_data = {"type": constant.TEAMS}
                for ws_field, ms_fields in team_schema.items():
                    team_data[ws_field] = team[ms_fields]
                if self.permission:
                    team_data["_allow_permissions"] = [team["id"]]
                documents.append(team_data)
        return documents

    def get_team_members(self):
        """ Fetches the team members from Microsoft Teams
            Returns:
                member_list: List having all the team members
        """
        member_list = {}
        teams_url = f"{constant.GRAPH_BASE_URL}/groups"
        try:
            teams_response = self.client.get(teams_url, constant.TEAMS, True, False, page_size=999, filter_query="/")
            team_response_data = check_response(
                self.logger, teams_response, "Could not fetch the teams from Microsoft Teams",
                "Error while fetching the teams from Microsoft Teams")
            if team_response_data:
                for team in team_response_data:
                    self.logger.info(f"Fetching team members for team: {team['displayName']}...")
                    team_id = team['id']
                    team_member_url = f"{constant.GRAPH_BASE_URL}/teams/{team_id}/members"
                    team_member_response = self.client.get(
                        team_member_url, constant.MEMBER, True, False, page_size=999, filter_query="/")
                    member_response_data = check_response(
                        self.logger, team_member_response, f"No team member found for team: {team['displayName']}",
                        f"Error while fetching the team members for team: {team['displayName']}")
                    if member_response_data:
                        for member in member_response_data:
                            display_name = member["displayName"]
                            member_list[display_name] = [*member_list.get(display_name, []) + [team_id]]
        except Exception as exception:
            self.logger.exception(f"Error while fetching the team members from Microsoft Teams. Error: {exception}")
            raise exception
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
            channel_url = f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels"
            self.logger.info(f"Fetching the channels for team: {team_name}")
            channel_response = self.client.get(channel_url, constant.CHANNELS, False, False)
            channel_response_data = check_response(
                self.logger, channel_response.json(),
                f"Could not fetch the channels for team: {team_name}",
                f"Error while fetching the channels for team: {team_name}")
            if channel_response_data:
                channel_schema = self.get_schema_fields("channels", self.objects)
                channels_by_team = {team_id: []}
                for channel in channel_response_data:
                    # Logic to append channels for deletion
                    insert_document_into_doc_id_storage(ids_list, channel["id"], constant.CHANNELS, team_id, "")
                    channel_data = {"type": constant.CHANNELS}
                    for ws_field, ms_field in channel_schema.items():
                        channel_data[ws_field] = channel[ms_field]
                    if self.permission:
                        channel_data["_allow_permissions"] = [team_id]
                    documents.append(channel_data)
                    channels_by_team[team_id].append(channel_data)
                documents_with_teams.append(channels_by_team)
        return documents_with_teams, documents

    def get_channel_messages(self, channels, ids_list, start_time, end_time):
        """ Fetches all the channel messages from the Microsoft Teams
            :param channels: All channels from Microsoft Teams
            :param ids_list: Shared storage for storing the document ids
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            Returns:
                documents: List of dictionaries containing the channel messages details
        """
        documents = []
        self.logger.debug(
            f"Fetching channel messages for the interval of start time: {start_time} and end time: {end_time}.")
        for each in channels:
            for team_id, channel_list in each.items():
                for channel in channel_list:
                    channel_id = channel["id"]
                    channel_name = channel["title"]
                    message_url = f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
                    try:
                        self.logger.info(f"Fetching the channel messages for channel: {channel_name}")
                        message_response = self.client.get(
                            message_url, constant.CHANNEL_MESSAGES, True, False, page_size=50,
                            filter_query=f"{start_time}/{end_time}")
                        message_response_data = check_response(
                            self.logger, message_response, f"Could not fetch the messages for channel: {channel_name}",
                            f"Error while fetching the messages for channel: {channel_name}")
                        if message_response_data:
                            documents = self.get_channel_messages_documents(
                                message_response_data, channel, ids_list, team_id, start_time, end_time, documents)
                    except Exception as exception:
                        self.logger.exception(
                            f"Error while fetching the channel messages from Microsoft Teams. Error: {exception}")
                        raise exception
        return documents

    def get_channel_messages_documents(
            self, message_response_data, channel, ids_list, team_id, start_time, end_time, documents):
        """Prepares a workplace search document to be indexed
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
        channel_message_schema = self.get_schema_fields("channel_messages", self.objects)
        for message_dict in message_response_data:
            message_data = {"type": constant.CHANNEL_MESSAGES}
            if not message_dict["deletedDateTime"]:
                content = html_to_text(self.logger, message_dict["body"]["content"])
                attachments = message_dict.get("attachments")
                is_meeting = message_dict.get("eventDetail") and message_dict.get(
                    "eventDetail", {}).get("callEventType")
                if content or attachments or is_meeting:
                    if content or attachments:
                        self.logger.info("Extracting html/text messages...")
                        sender = message_dict["from"]["user"]["displayName"]
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
                        meeting_time = message_dict['createdDateTime']
                        formatted_datetime = dateparser.parse(meeting_time).strftime(
                            "%d %b, %Y at %H:%M:%S")
                        message_data["title"] = f"{channel['title']} - Meeting On "\
                                                f"{formatted_datetime}"

                    # Logic to append channel messages for deletion
                    insert_document_into_doc_id_storage(
                        ids_list, message_dict["id"],
                        constant.CHANNEL_MESSAGES, channel_id, team_id)
                    for ws_field, ms_field in channel_message_schema.items():
                        message_data[ws_field] = message_dict[ms_field]
                    if self.permission:
                        message_data["_allow_permissions"] = [team_id]
                    replies_data = self.get_message_replies(
                        team_id, channel_id, message_dict['id'], start_time, end_time)
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
        """Creates a variable having the attachment names
        :param attachments: Attachment object for fetching the attachment names
        Returns:
            attachment_names: Variable having the attachment names
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
        replies_url = f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
        self.logger.info(f"Fetching message replies for message id: {message_id}...")
        replies_response = self.client.get(replies_url, constant.CHANNEL_MESSAGES,
                                           True, False, page_size=50, filter_query=f"{start_time}/{end_time}")
        replies_response_data = check_response(
            self.logger, replies_response, "Could not fetch the channel message replies.",
            "Error while fetching the channel message replies.")
        if not replies_response_data:
            return None
        replies_list = []
        for reply in replies_response_data:
            reply_content = html_to_text(self.logger, reply["body"]["content"])
            if reply_content:
                sender = reply["from"]["user"]["displayName"]
                replies_list.append(f"{sender} - {reply_content}")
        message_body = "\n".join(reply for reply in replies_list)
        return message_body

    def get_channel_tabs(self, channels, ids_list, start_time, end_time):
        """ Fetches the channel tabs from the Microsoft Teams.
            :param channels: All channels from Microsoft Teams
            :param ids_list: Shared storage for storing the document ids
            :param start_time: Starting time for fetching data
            :param end_time: Ending time for fetching data
            Returns:
                documents: Documents to be indexed in Workplace Search
        """
        documents = []
        self.logger.debug(
            f"Fetching channel tabs for the interval of start time: {start_time} and end time: {end_time}.")
        for each in channels:
            for team_id, channel_list in each.items():
                for channel in channel_list:
                    channel_id = channel["id"]
                    channel_name = channel['title']
                    self.logger.info(f"Fetching the tabs for channel: {channel_name}")
                    tabs_response = self.client.get(
                        f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels/{channel_id}/tabs",
                        constant.CHANNEL_TABS, False, False,
                        datetime_filter_column_name="dateAdded",
                        filter_query=f"{start_time}/{end_time}", is_pandas_series=True)
                    tabs_response_data = check_response(
                        self.logger, tabs_response, f"Could not fetch tabs for channel: {channel_name}",
                        f"Error while fetching tabs for channel: {channel_name}")
                    if tabs_response_data:
                        tabs_schema = self.get_schema_fields("channel_tabs", self.objects)
                        for tabs_dict in tabs_response_data:
                            # Logic to append channel tabs for deletion
                            insert_document_into_doc_id_storage(
                                ids_list, tabs_dict["id"], constant.CHANNEL_TABS, channel_id, team_id)
                            tabs_data = {"type": constant.CHANNEL_TABS}
                            for ws_field, ms_field in tabs_schema.items():
                                if ws_field == "title":
                                    tabs_data[ws_field] = f"{channel_name}-{tabs_dict[ms_field]}"
                                else:
                                    tabs_data[ws_field] = tabs_dict[ms_field]
                            if self.permission:
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
            drive_response = self.client.get(
                f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives", constant.DRIVE, True, False, page_size=5000,
                filter_query="/")
            drive_response_data = check_response(
                self.logger, drive_response,
                f"Could not fetch channels document drives for team:{team_id} Error: {drive_response}",
                f"Error while fetching channels document drives for team: {team_id} Error: {drive_response}")
            if drive_response_data:
                for drive in drive_response_data:
                    drive_id = drive["id"]
                    self.logger.info(f"Fetching root for drive: {drive['name']}")
                    # Logic to append team drives ids for deletion
                    insert_document_into_doc_id_storage(ids_list, drive_id, constant.CHANNEL_DRIVE, team_id, "")
                    root_response = self.client.get(
                        f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives/{drive_id}/root",
                        constant.ROOT, False, False, filter_query="/")
                    if root_response:
                        try:
                            root_response_data = root_response.json()
                        except JSONDecodeError as exception:
                            self.logger.exception(
                                f"Error while fetching the drive root response data from drive id: {drive_id} and "
                                f"team: {team_name}. Error: {exception}")
                            continue
                        root_id = root_response_data["id"]
                        self.logger.info(f"Fetching channel drives for root: {root_response_data['name']}")
                        # Logic to append drive roots ids for deletion
                        insert_document_into_doc_id_storage(
                            ids_list, root_id, constant.CHANNEL_ROOT, drive_id, team_id)
                        children_response = self.client.get(
                            f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives/{drive_id}/items/{root_id}/children",
                            constant.DRIVE, True, False, page_size=5000, filter_query="/")
                        children_response_data = check_response(
                            self.logger, children_response,
                            f"Could not fetch channels document drive items for team:{team_id} Error: "
                            f"{children_response}", "Error while fetching channels document drive items for team: "
                            f"{team_id} Error: {children_response}")
                        if children_response_data:
                            document_schema = self.get_schema_fields("channel_documents", self.objects)
                            for child in children_response_data:
                                # Logic to append drive item ids for deletion
                                insert_document_into_doc_id_storage(
                                    ids_list, child["id"], constant.CHANNEL_DRIVE_ITEM, root_id, drive_id)
                                folder_documents = self.get_folder_documents(
                                    team_id, drive_id, child["id"],
                                    document_schema, [],
                                    ids_list, child["id"],
                                    start_time, end_time)
                                if folder_documents:
                                    documents.extend(folder_documents)
        return list(unique_everseen(documents))

    def get_folder_documents(
            self, team_id, drive_id, document_id, schema, documents, ids_list, parent_file_id, start_time,
            end_time):
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
            Returns:
                documents: list of documents containing the channel documents details
        """
        folder_files_url = f"{constant.GRAPH_BASE_URL}/groups/{team_id}/drives/{drive_id}/items/{document_id}/children"
        folder_files_response = self.client.get(
            folder_files_url, constant.CHANNEL_DOCUMENTS, True, False, page_size=5000,
            filter_query=f"{start_time}/{end_time}")
        folder_files_response_data = check_response(
            self.logger, folder_files_response,
            f"Could not fetch folder documents for team:{team_id} Error: {folder_files_response}",
            f"Error while fetching folder documents for team: {team_id} Error: {folder_files_response}")
        if folder_files_response_data:
            for document in folder_files_response_data:
                # Logic to append recursive files/folders for deletion
                insert_document_into_doc_id_storage(
                    ids_list, document["id"], constant.CHANNEL_DOCUMENTS, document_id, parent_file_id)
                document_data = {"type": constant.CHANNEL_DOCUMENTS}
                if document.get("folder") and type(document.get("folder")) != float:
                    self.get_folder_documents(
                        team_id, drive_id, document["id"],
                        schema, documents, ids_list, document_id, start_time, end_time)
                for ws_field, ms_field in schema.items():
                    document_data[ws_field] = document[ms_field]
                if self.permission:
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
