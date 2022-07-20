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
