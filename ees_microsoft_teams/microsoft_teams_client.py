#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module queries Microsoft Teams Graph API and returns the parsed response.
"""
from . import constant
from .microsoft_teams_requests import (
    MSTeamsRequests,
    TooManyRequestException,
    QueryBuilder,
)
from .utils import retry, get_data_from_http_response


class MSTeamsClient(MSTeamsRequests):
    """This class uses the MicrosoftTeamsRequests class to fetch all the supported Microsoft Teams objects and return
    the parsed response
    """

    def __init__(self, logger, access_token, config):
        self.access_token = access_token
        self.logger = logger
        self.config = config
        self.query_builder = QueryBuilder()
        self.retry_count = int(config.get_value("retry_count"))

    def get_teams(self, next_url):
        """ Get teams from the Microsoft Teams with the support of pagination and
            filtration.
            :param next_url: URL to invoke Graph API call
        """
        response_list = {"value": []}
        while next_url:
            try:
                query = self.query_builder.get_query_for_teams().strip()
                url = f"{next_url}{query}"
                response_json = self.get(url=url, object_type=constant.TEAMS)
                response_list["value"].extend(response_json.get("value"))

                next_url = response_json.get("@odata.nextLink")

                if not next_url or next_url == url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception(
                    f"Error while fetching the Microsoft Team. Error: {unknown_exception}"
                )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message="Could not fetch the teams from Microsoft Teams",
            exception_message="Error while fetching the teams from Microsoft Teams",
        )

        return parsed_response

    @retry(exception_list=(TooManyRequestException))
    def get_channels(self, next_url):
        """ Get channels from the Microsoft Teams
            :param next_url: URL to invoke Graph API call
        """
        try:
            response = self.get(url=next_url, object_type=constant.CHANNELS)
            parsed_response = get_data_from_http_response(
                logger=self.logger,
                response=response,
                error_message="Could not fetch the teams from Microsoft Teams",
                exception_message="Error while fetching the teams from Microsoft Teams",
            )
            return parsed_response

        except Exception as unknown_exception:
            self.logger.exception(
                f"Error while fetching the Microsoft Team. Error: {unknown_exception}"
            )

    def get_channel_messages(self, next_url, start_time, end_time, channel_name="", is_message_replies=False):
        """ Get channel messages from the Microsoft Teams with the support of pagination and
            filtration.
            :param next_url: URL to invoke Graph API call
            :param start_time: Starting time to fetch channel messages
            :param end_time: Ending time to fetch channel messages
            :param channel_name: Channel for fetching messages
            :param is_message_replies: Flag to check if method is used for fetching message replies
        """
        response_list = {"value": []}
        while next_url:
            try:
                query = self.query_builder.get_query_for_channel_and_chat_messages().strip()
                url = f"{next_url}{query}"
                response_json = self.get(url=url, object_type=constant.CHANNEL_MESSAGES)

                # Filter response based on lastModifiedDateTime
                response_value = response_json.get("value")
                if response_value:
                    for message in response_value:
                        last_modified_date_time = message.get("lastModifiedDateTime")
                        if start_time <= last_modified_date_time <= end_time:
                            response_list["value"].append(message)

                next_url = response_json.get("@odata.nextLink")

                if not next_url or next_url == url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception(f"Error while fetching the Microsoft Team. Error: {unknown_exception}")

        if is_message_replies:
            return response_list

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch the messages for channel: {channel_name}",
            exception_message=f"Error while fetching the messages for channel: {channel_name}"
        )
        return parsed_response

    def get_channeL_tabs(self, next_url, start_time, end_time, channel_name):
        """ Get channel tabs from the Microsoft Teams with the support of pagination and
            filtration.
            :param next_url: URL to invoke Graph API call
            :param start_time: Starting time to fetch channel tabs
            :param end_time: Ending time to fetch channel tabs
            :param channel_name: Channel for fetching channel tabs
        """
        response_list = {"value": []}
        while next_url:
            try:
                response_json = self.get(url=next_url, object_type=constant.CHANNEL_MESSAGES)

                # Filter response based on dateAdded
                response_value = response_json.get("value")
                if response_value:
                    for tab in response_value:
                        date_added = tab.get("configuration").get("dateAdded")
                        if not date_added:
                            response_list["value"].append(tab)
                        elif start_time <= date_added <= end_time:
                            response_list["value"].append(tab)

                next_url = response_json.get("@odata.nextLink")

                if not next_url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception(f"Error while fetching the Microsoft Team. Error: {unknown_exception}")

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch tabs for channel: {channel_name}",
            exception_message=f"Error while fetching tabs for channel: {channel_name}")
        return parsed_response
