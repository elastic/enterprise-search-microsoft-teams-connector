#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module queries Microsoft Teams Graph API and returns the parsed response.
"""

import time

from . import constant
from .microsoft_teams_requests import (
    MSTeamsRequests,
    TooManyRequestException,
    QueryBuilder,
)
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

            except TooManyRequestException as exception:
                self.logger.error(
                    f"{exception.message}. Retrying in {exception.retry_after_seconds} seconds"
                )
                time.sleep(exception.retry_after_second)
                continue

            except Exception as unknown_exception:
                self.logger.exception(
                    f"Error while fetching the Microsoft Team. Error: {unknown_exception}"
                )

        return response_list

    @retry(exception_list=(TooManyRequestException))
    def get_channels(self, next_url):
        """ Get channels from the Microsoft Teams
            :param next_url: URL to invoke Graph API call
        """
        try:
            return self.get(url=next_url, object_type=constant.CHANNELS)
        except TooManyRequestException as exception:
            self.logger.error(
                f"{exception.message}. Retrying in {exception.retry_after_seconds} seconds"
            )
            time.sleep(exception.retry_after_second)
            raise exception
        except Exception as unknown_exception:
            self.logger.exception(
                f"Error while fetching the Microsoft Team. Error: {unknown_exception}"
            )
