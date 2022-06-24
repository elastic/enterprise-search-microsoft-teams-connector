#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module collects all the teams and Channels detail from Microsoft Teams.
"""
from . import constant
from .microsoft_teams_client import MSTeamsClient
from .utils import (get_data_from_http_response, get_schema_fields)

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
        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response,
            error_message="Could not fetch the teams from Microsoft Teams",
            exception_message="Error while fetching the teams from Microsoft Teams",
        )

        if not parsed_response:
            return []

        team_schema = get_schema_fields("teams", self.object_type_to_index)
        for team in parsed_response:
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
        self.logger.info("Fetching the team members from Microsoft Teams")

        member_list = {}
        response = self.client.get_teams(next_url=f"{constant.GRAPH_BASE_URL}/groups")
        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response,
            error_message="Could not fetch the teams from Microsoft Teams",
            exception_message="Error while fetching the teams from Microsoft Teams",
        )

        if not parsed_response:
            return member_list

        for team in parsed_response:
            self.logger.info(f"Fetching members for the team: {team['displayName']}")
            team_id = team["id"]
            response = self.client.get_teams(
                next_url=f"{constant.GRAPH_BASE_URL}/teams/{team_id}/members"
            )
            parsed_response = get_data_from_http_response(
                logger=self.logger,
                response=response,
                error_message=f"No team member found for team: {team['displayName']}",
                exception_message=f"Error while fetching the team members for team: {team['displayName']}",
            )

            if not parsed_response:
                return {}

            for member in parsed_response:
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
            self.logger.info(f"Fetching the channels for team: {team_name}")

            response = self.client.get_channels(
                next_url=f"{constant.GRAPH_BASE_URL}/teams/{team_id}/channels"
            )
            parsed_response = get_data_from_http_response(
                logger=self.logger,
                response=response,
                error_message=f"Could not fetch the channels for team: {team_name}",
                exception_message=f"Error while fetching the channels for team: {team_name}",
            )

            if not parsed_response:
                continue

            channel_schema = get_schema_fields("channels", self.object_type_to_index)
            channels_by_team = {team_id: []}
            for channel in parsed_response:
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
