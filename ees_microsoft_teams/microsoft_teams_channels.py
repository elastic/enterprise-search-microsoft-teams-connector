#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module collects all the teams and Channels detail from Microsoft Teams.
"""
import dateparser  # noqa

from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import (check_response, insert_document_into_doc_id_storage)

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
