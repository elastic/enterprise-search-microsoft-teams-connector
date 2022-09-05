#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module queries Microsoft Teams Graph API and returns the parsed response.
"""

from json import JSONDecodeError

import requests
import time
from requests.exceptions import RequestException
from requests.models import Response

from . import constant
from .msal_access_token import MSALAccessToken
from .utils import retry


class ResponseException(Exception):
    """Exception raised when there is an internal server error encountered by connecting to the Microsoft Teams using
    Graph APIs.
    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class UnauthorizedException(Exception):
    """Exception raised when there is an Unauthorized status code(401) encountered while connecting to the Microsoft
    Teams using Graph APIs. The possible reason for this exception can be expiry of the access token.
    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class TooManyRequestException(Exception):
    """Exception raised when the Microsoft server throws too many requests exception(status code=429) while connecting
    to the Microsoft Teams using Graph APIs.
    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class QueryBuilder(object):
    """This class builds the query for the Microsoft Graph APIs based on different object types to be fetched.
    The possible object types are Teams, Channels, Chats, Meetings, etc.
    """

    def __init__(self) -> None:
        pass

    def get_query_for_teams(self, page_size=999):
        return f"?$top={page_size}"

    def get_query_for_channel_and_chat_messages(self, page_size=50):
        return f"?$top={page_size}"

    def get_query_for_drives_and_docs(self, page_size=5000):
        return f"?$top={page_size}"

    def get_query_for_user_chats(self, page_size=50):
        return f"&$top={page_size}"

    def get_query_for_calendars(self, start_time, end_time, page_size=50):
        return f"?$filter=lastModifiedDateTime ge {start_time} and lastModifiedDateTime le {end_time}&$top={page_size}"


class MSTeamsRequests:
    """This class invokes GET call to the Microsoft Graph API and handles the errors."""

    def __init__(self, logger, access_token, config):
        self.access_token = access_token
        self.logger = logger
        self.config = config
        self.retry_count = int(config.get_value("retry_count"))

    @retry(exception_list=(RequestException, ResponseException, UnauthorizedException, TooManyRequestException))
    def get(self, url, object_type):
        """Invokes a GET call to the Microsoft Graph API
        :param url: Request URL to call the Graph API
        :param object_type: The type of the object to get. The allowed values are teams, channels, channel_chat,
            channel_documents, user_chats, etc.
        Returns:
            Parsed object of the GET call
        """
        try:
            response = requests.get(url, headers={"Authorization": f"Bearer {self.access_token}"})
            status_code = response.status_code

            if status_code not in [200, 403, 404]:
                raise RequestException(
                    f"{response.reason}. Error while fetching {object_type} from Microsoft "
                    f"Teams, url: {url}"
                )

            if status_code == requests.codes.ok:
                return self.parse_response_object(response)

            elif status_code in range(400, 500):
                if status_code == 401:
                    self.regenerate_token(object_type=object_type)
                    raise UnauthorizedException
                elif status_code == 429:
                    retry_after_seconds = int(response.headers.get("Retry-After", 60))
                    time.sleep(retry_after_seconds)
                    raise TooManyRequestException(
                        message="Received TooManyRequestException while fetching the Teams"
                    )
                else:
                    return self.handle_4xx_errors(
                        response=response, object_type=object_type, request_url=url
                    )
        except RequestException as exception:
            raise exception

    def parse_response_object(self, response):
        """Parse the response object received from the HTTP Request
        :param response: Response object from Microsoft Graph API
        """
        response_data = {}
        try:
            response_data = response.json()
        except JSONDecodeError as exception:
            self.logger.exception(
                f"Error while fetching the response data. Error: {exception}"
            )
        return response_data

    def regenerate_token(self, object_type):
        """Regenerates the access token in case of access token has expired
        :param object_type: The type of the object to get. The allowed values are teams, channels, channel_chat,
        channel_docs, calendar, user_chats, permissions and deletion
        """
        self.logger.warn("Access Token has expired. Regenerating the access token...")
        token = MSALAccessToken(self.logger, self.config)

        # Unable to fetch the CALENDAR and ATTACHMENT using the access token generated via user-password flow
        # So generating the separate access token for fetching CALENDAR and ATTACHMENT objects
        if object_type in [constant.CALENDAR, constant.ATTACHMENTS]:
            self.access_token = token.get_token(is_acquire_for_client=True)
        else:
            self.access_token = token.get_token()

    def handle_4xx_errors(self, response, object_type, request_url):
        """Returns the response when 4xx error occurs
        :param response: Response from Microsoft Graph API request
        :param object_type: The type of the object to get. The allowed values are teams, channels, channel_chat,
            channel_docs, calendar, user_chats, permissions and deletion
        :param request_url: Request URL for logging the message
        """
        response_data = self.parse_response_object(response)
        # Error 403 occurs when the current user is trying fetch the Teams and it's object which was
        # created by other user
        if response.status_code == 403 or (
            response.status_code == 404
            and response_data.get("error", {}).get("code") == "NotFound"
        ):
            if object_type not in [
                constant.CHANNELS,
                constant.ATTACHMENTS,
                constant.ROOT,
            ]:
                return {"value": []}

            new_response = Response()
            new_response._content = b'{"value": []}'
            new_response.status_code = 200
            return self.parse_response_object(new_response)
        elif not (object_type == "deletion" and response.status_code == 404):
            self.logger.error(
                f"Error: {response.reason}. Error while fetching {object_type} from Microsoft Teams, "
                f"url: {request_url}."
            )

        return response
