#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module collects all the teams and Channels detail from Microsoft Teams.
"""
from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import (get_data_from_http_response, insert_document_into_doc_id_storage, get_schema_fields)

MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
CHANNEL_MEETINGS = "Channel Meetings"
TEAMS_PAGE_SIZE = 999


class MSTeamsChannels:
    """This class fetches all the teams and channels data from Microsoft Teams.
    """

    def __init__(self, access_token, logger, config):
        self.access_token = access_token
        self.client = MSTeamsClient(logger, self.access_token, config)
        self.logger = logger
        self.objects_to_be_indexed = config.get_value('objects')
        self.is_permission_sync_enabled = config.get_value("enable_document_permission")

    def get_all_teams(self, ids_list):
        """ Fetches all the teams from Microsoft Teams
            :param ids_list: Shared storage for storing the document ids
            Returns:
                teams_details: List of dictionaries containing the team details
        """
        documents = []
        teams_url = f"{constant.GRAPH_BASE_URL}/groups"
        self.logger.info("Fetching teams from Microsoft Teams...")
        team_response = self.client.get(teams_url, constant.TEAMS, is_pagination=True, is_filter=False,
                                        page_size=TEAMS_PAGE_SIZE, filter_query="/")
        team_response_data = get_data_from_http_response(
            self.logger, team_response, "Could not fetch the teams from Microsoft Teams",
            "Error while fetching the teams from Microsoft Teams")
        if team_response_data:
            team_schema = get_schema_fields("teams", self.objects_to_be_indexed)
            for team in team_response_data:
                # Logic to append teams for deletion
                insert_document_into_doc_id_storage(ids_list, team["id"], constant.TEAMS, "", "")
                team_data = {"type": constant.TEAMS}
                for workplace_search_field, microsoft_teams_fields in team_schema.items():
                    team_data[workplace_search_field] = team[microsoft_teams_fields]
                if self.is_permission_sync_enabled:
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
            teams_response = self.client.get(teams_url, constant.TEAMS, is_pagination=True, is_filter=False,
                                             page_size=TEAMS_PAGE_SIZE, filter_query="/")
            team_response_data = get_data_from_http_response(
                self.logger, teams_response, "Could not fetch the teams from Microsoft Teams",
                "Error while fetching the teams from Microsoft Teams")
            if team_response_data:
                for team in team_response_data:
                    self.logger.info(f"Fetching team members for team: {team['displayName']}...")
                    team_id = team['id']
                    team_member_url = f"{constant.GRAPH_BASE_URL}/teams/{team_id}/members"
                    team_member_response = self.client.get(
                        team_member_url, constant.MEMBER, is_pagination=True, is_filter=False,
                        page_size=TEAMS_PAGE_SIZE, filter_query="/")
                    member_response_data = get_data_from_http_response(
                        self.logger, team_member_response, f"No team member found for team: {team['displayName']}",
                        f"Error while fetching the team members for team: {team['displayName']}")
                    if member_response_data:
                        for member in member_response_data:
                            display_name = member["displayName"]
                            if member_list.get(display_name):
                                member_list[display_name].append(team_id)
                            else:
                                member_list[display_name] = [team_id]
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
            self.logger.info(f"Fetching channels for team: {team_name}")
            channel_response = self.client.get(channel_url, constant.CHANNELS, is_pagination=False, is_filter=False)
            channel_response_data = get_data_from_http_response(
                self.logger, channel_response.json(),
                f"Could not fetch the channels for team: {team_name}",
                f"Error while fetching the channels for team: {team_name}")
            if channel_response_data:
                channel_schema = get_schema_fields("channels", self.objects_to_be_indexed)
                channels_by_team = {team_id: []}
                for channel in channel_response_data:
                    # Logic to append channels for deletion
                    insert_document_into_doc_id_storage(ids_list, channel["id"], constant.CHANNELS, team_id, "")
                    channel_data = {"type": constant.CHANNELS}
                    for ws_field, ms_field in channel_schema.items():
                        channel_data[ws_field] = channel[ms_field]
                    if self.is_permission_sync_enabled:
                        channel_data["_allow_permissions"] = [team_id]
                    documents.append(channel_data)
                    channels_by_team[team_id].append(channel_data)
                documents_with_teams.append(channels_by_team)
        return documents_with_teams, documents
