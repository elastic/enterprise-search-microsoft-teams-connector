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

    def get_channel_tabs(self, next_url, start_time, end_time, channel_name):
        """ Get channel tabs from the Microsoft Teams with the support of filtration.
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
                self.logger.exception("Error while fetching the channel tabs from Microsoft Team. "
                                      f"Error: {unknown_exception}")

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch tabs for channel: {channel_name}",
            exception_message=f"Error while fetching tabs for channel: {channel_name}")
        return parsed_response

    def get_channel_drives_and_children(self, next_url, object_type, team_name=""):
        """ Get channel documents from the Microsoft Teams with the support of pagination and filtration.
            :param next_url: URL to invoke Graph API call
            :param object_type: Object type to call the GET api
            :param team_name: Team for fetching channel documents
        """
        response_list = {"value": []}
        try:
            query = self.query_builder.get_query_for_drives_and_docs().strip()
            url = f"{next_url}{query}"
            response_json = self.get(url=url, object_type=object_type)
            return response_json

        except Exception as unknown_exception:
            self.logger.exception(
               f"Error while fetching channel documents the Microsoft Team. Error: {unknown_exception}"
            )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch the channel documents for team: {team_name}",
            exception_message=f"Error while fetching the channel documents for team: {team_name}"
        )
        return parsed_response

    def get_channel_documents(self, next_url, start_time, end_time, object_type, team_name=""):
        """ Get channel documents from the Microsoft Teams with the support of pagination and filtration.
            :param next_url: URL to invoke Graph API call
            :param start_time: Starting time to fetch channel documents
            :param end_time: Ending time to fetch channel documents
            :param object_type: Object type to call the GET api
            :param team_name: Team for fetching channel documents
        """
        response_list = {"value": []}
        while next_url:
            try:
                query = self.query_builder.get_query_for_drives_and_docs().strip()
                url = f"{next_url}{query}"

                # The hierarchy(teams > drives > root > children i.e. actual files/folders) through which channel
                # documents gets fetched. So, due to this `object_type` argument is used to differentiate the objects.
                response_json = self.get(url=url, object_type=object_type)

                response_value = response_json.get("value")
                if response_value:
                    for channel_document in response_value:
                        if channel_document.get("folder"):
                            response_list["value"].append(channel_document)

                        else:
                            last_modified_date_time = channel_document.get("lastModifiedDateTime")
                            if start_time <= last_modified_date_time <= end_time:
                                response_list["value"].append(channel_document)

                next_url = response_json.get("@odata.nextLink")

                if not next_url or next_url == url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception("Error while fetching channel documents the Microsoft Team. Error: "
                                      f"{unknown_exception}")

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch the channel documents for team: {team_name}",
            exception_message=f"Error while fetching the channel documents for team: {team_name}"
        )
        return parsed_response

    def get_user_chats(self, next_url):
        """ Get user chats from the Microsoft Teams with the support of pagination and filtration.
            :param next_url: URL to invoke Graph API call
        """
        response_list = {"value": []}
        is_calling_first_time = True
        while next_url:
            try:
                query = self.query_builder.get_query_for_user_chats().strip()
                if is_calling_first_time:
                    url = f"{next_url}{query}"
                    is_calling_first_time = False
                else:
                    url = next_url
                response_json = self.get(url=url, object_type=constant.CHATS)
                response_list["value"].extend(response_json.get("value"))

                next_url = response_json.get("@odata.nextLink")

                if not next_url or next_url == url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception(
                    f"Error while fetching user chats from the Microsoft Teams. Error: {unknown_exception}"
                )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message="Could not fetch the User Chats from Microsoft Teams",
            exception_message="Error while fetching the User Chats from Microsoft Teams",
        )

        return parsed_response

    def get_user_chat_messages(self, next_url, start_time, end_time, chat_id):
        """ Get user chat messages from the Microsoft Teams with the support of pagination and filtration.
            :param next_url: URL to invoke Graph API call
            :param start_time: Starting time to fetch user chats messages
            :param end_time: Ending time to fetch user chat messages
            :param chat_id: Chat ID to fetch user chat messages
        """
        response_list = {"value": []}
        is_calling_first_time = True
        while next_url:
            try:
                query = self.query_builder.get_query_for_user_chats_messages().strip()
                if is_calling_first_time:
                    url = f"{next_url}{query}"
                    is_calling_first_time = False
                else:
                    url = next_url
                response_json = self.get(url=url, object_type=constant.USER_CHATS_MESSAGE)

                # Filter response based on lastModifiedDateTime
                response_value = response_json.get("value")
                if response_value:
                    for chat_message in response_value:
                        last_modified_date_time = chat_message.get("lastModifiedDateTime")
                        if start_time <= last_modified_date_time <= end_time:
                            response_list["value"].append(chat_message)

                next_url = response_json.get("@odata.nextLink")

                if not next_url or next_url == url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception(
                    f"Error while fetching the Microsoft User Chats Messages. Error: {unknown_exception}"
                )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch the User Chats Messages from Microsoft Teams for chat id: {chat_id}",
            exception_message=f"Error while fetching User Chats Messages from Microsoft Teams for chat id: {chat_id}",
        )

        return parsed_response

    def get_user_chat_tabs(self, next_url, start_time, end_time, chat_id):
        """ Get user chat tabs from the Microsoft Teams with the support of pagination and filtration.
            :param next_url: URL to invoke Graph API call
            :param start_time: Starting time to fetch user chats tabs
            :param end_time: Ending time to fetch user chat tabs
            :param chat_id: Chat ID to fetch user chat tabs
        """
        response_list = {"value": []}
        try:
            response_json = self.get(url=next_url, object_type=constant.USER_CHAT_TABS)
            if response_json:
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
            self.logger.exception(
                f"Error while fetching the Microsoft User Chats Tabs. Error: {unknown_exception}"
            )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message=f"Could not fetch the User Chats Tabs from Microsoft Teams for chat id: {chat_id}",
            exception_message=f"Error while fetching the User Chats Tabs from Microsoft Teams for chat id: {chat_id}",
        )

        return parsed_response

    def get_user_chat_attachment_drive(self, next_url):
        """ Get user chat attachment drives from the Microsoft Teams.
            :param next_url: URL to invoke Graph API call
        """
        response_json = None
        try:
            response_json = self.get(url=next_url, object_type=constant.ATTACHMENTS)

        except Exception as unknown_exception:
            self.logger.exception(
                f"Error while fetching the Microsoft User Chat Attachment. Error: {unknown_exception}"
            )
        return response_json

    def get_user_chat_attachment_drive_children(self, next_url):
        """ Get user chat attachments from the Microsoft Teams.
            :param next_url: URL to invoke Graph API call
        """
        response_list = {"value": []}
        try:
            response_json = self.get(url=next_url, object_type=constant.ATTACHMENTS)
            response_list["value"].extend(response_json.get("value"))

        except Exception as unknown_exception:
            self.logger.exception(
                f"Error while fetching the Microsoft User Chat Attachment. Error: {unknown_exception}"
            )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message="Could not fetch the User Chat Attachment from Microsoft Teams",
            exception_message="Error while fetching the User Chat Attachment from Microsoft Teams",
        )

        return parsed_response

    def get_calendars(self, next_url, start_time, end_time):
        """ Get calendar events from the Microsoft Teams with the support of pagination and
            filtration.
            :param next_url: URL to invoke Graph API call
            :param start_time: Starting time to fetch calendar events
            :param end_time: Ending time to fetch calendat events
        """
        response_list = {"value": []}
        while next_url:
            try:
                query = self.query_builder.get_query_for_calendars(start_time, end_time).strip()
                url = f"{next_url}{query}"
                response_json = self.get(url=url, object_type=constant.CALENDAR)
                response_list["value"].extend(response_json.get("value"))

                next_url = response_json.get("@odata.nextLink")

                if not next_url or next_url == url:
                    next_url = None

            except Exception as unknown_exception:
                self.logger.exception(
                    f"Error while fetching calendar events from the Microsoft Teams. Error: {unknown_exception}"
                )

        parsed_response = get_data_from_http_response(
            logger=self.logger,
            response=response_list,
            error_message="Could not fetch the teams from Microsoft Teams",
            exception_message="Error while fetching the teams from Microsoft Teams",
        )

        return parsed_response
