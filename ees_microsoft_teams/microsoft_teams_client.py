#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module queries Microsoft Teams Graph API and returns the parsed response.
"""

from json import JSONDecodeError
import time
import pandas
import requests
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


class MSTeamsClient:
    """This class invokes GET call to the Microsoft Graph API on the basis of pagination and filters."""

    def __init__(self, logger, access_token, config):
        self.access_token = access_token
        self.logger = logger
        self.config = config
        self.retry_count = int(config.get_value("retry_count"))
        self.request_header = {
            "Authorization": f"Bearer {self.access_token}"
        }

    @retry(exception_list=(RequestException, ResponseException))
    def get(self, url, object_type, is_pagination, is_filter, page_size=0, filter_query="",
            datetime_filter_column_name="lastModifiedDateTime", is_pandas_series=False):
        """ Invokes a GET call to the Microsoft Graph API
            :param url: Base url to call the Graph API
            :param object_type: Parameter name whether it is teams, channels, channel_chat, channel_docs, calendar,
                user_chats, permissions or deletion
            :param is_pagination: Flag to check if pagination is enabled
            :param is_filter: Flag to check if filter is enabled
            :param page_size: Size of the top variable for pagination
            :param filter_query: Filter query if filter is enabled
            :param datetime_filter_column_name: Filter query if is_pandas_series enabled
            :param is_pandas_series: Flag to check if pandas series is enabled
            Returns:
                Response of the GET call
        """
        response_list = {"value": []}
        flag = True
        paginate_query = True
        while paginate_query:
            if flag and is_pagination and is_filter:
                paginate_query = f"?$filter={filter_query}&$top={page_size}"
            elif flag and is_pagination and not is_filter:
                if object_type == constant.CHATS:
                    paginate_query = f"&$top={page_size}"
                else:
                    paginate_query = f"?$top={page_size}"
                start_time = filter_query.split("/")[0]
                end_time = filter_query.split("/")[1]
            elif is_filter and not is_pagination:
                paginate_query = f"?$filter={filter_query}"
            else:
                if object_type not in [constant.CHANNELS, constant.CALENDAR]:
                    start_time = filter_query.split("/")[0]
                    end_time = filter_query.split("/")[1]
                paginate_query = " "

            request_url = f"{url}{paginate_query.strip()}"
            flag = False
            try:
                response = requests.get(
                    request_url,
                    headers=self.request_header
                )
                if response and response.status_code == requests.codes.ok:
                    if is_pagination and not is_filter:
                        response_data = self.get_response_data(response)
                        if object_type in [
                                constant.MEMBER, constant.TEAMS, constant.CHATS, constant.DRIVE, constant.CALENDAR]:
                            response_list["value"].extend(response_data.get("value"))
                        else:
                            data_frame = pandas.DataFrame(response_data.get("value"))
                            if not data_frame.empty:
                                row = data_frame
                                # Fetch the folders data from Microsoft Teams response
                                if "folder" in data_frame.columns:
                                    # Filtered data for folders
                                    folder_data = data_frame.loc[data_frame["folder"].notnull()].to_dict('records')
                                    response_list["value"].extend(folder_data)

                                    # Filtered data for files
                                    row = data_frame.loc[data_frame["folder"].isnull()]
                                data_frame.lastModifiedDateTime = pandas.to_datetime(data_frame.lastModifiedDateTime)
                                filtered_df = row.loc[(data_frame['lastModifiedDateTime'] >= start_time) & (
                                    data_frame['lastModifiedDateTime'] < end_time)]
                                filter_data = filtered_df.to_dict('records')
                                response_list["value"].extend(filter_data)
                        url = response_data.get("@odata.nextLink")
                        if not url or url == request_url:
                            paginate_query = None
                        break
                    elif is_pagination and is_filter:
                        response_data = self.get_response_data(response)
                        response_list["value"].extend(response_data.get("value"))
                        url = response_data.get("@odata.nextLink")
                        if not url:
                            paginate_query = None
                        break
                    elif not (object_type in [
                            constant.CHANNELS, constant.ROOT, constant.ATTACHMENTS] or is_pagination or is_filter):
                        response_data = self.get_response_data(response)
                        data_frame = pandas.DataFrame(response_data.get("value"))
                        if not data_frame.empty:
                            rows = data_frame
                            if is_pandas_series:
                                rows = data_frame.configuration.apply(pandas.Series)
                            # Add column if not present in data frame
                            if datetime_filter_column_name not in rows.columns:
                                rows[datetime_filter_column_name] = start_time

                            # Set start_time if value of "datetime_filter_column_name" column is null for any
                            # specific row
                            rows.loc[rows[datetime_filter_column_name].isnull(),
                                     datetime_filter_column_name] = start_time
                            rows[datetime_filter_column_name] = pandas.to_datetime(rows[datetime_filter_column_name])
                            filtered_df = data_frame.loc[(rows[datetime_filter_column_name] >= start_time) & (
                                rows[datetime_filter_column_name] < end_time)]
                            filter_data = filtered_df.to_dict('records')
                            response_list["value"].extend(filter_data)

                        paginate_query = None
                        break
                    else:
                        return response
                elif response.status_code >= 400 and response.status_code < 500:
                    if response.status_code == 401:
                        self.regenerate_token(object_type)
                        continue
                    if response.status_code == 429:
                        time.sleep(int(response.headers["Retry-After"]))
                        continue
                    response_data = self.get_response_data(response)
                    # Error 403 occurs when the current user is trying fetch the Teams and it's object which was
                    # created by other user
                    if response.status_code == 403 or (
                            response.status_code == 404 and response_data.get("error", {}).get("code") == "NotFound"):
                        if object_type in [constant.CHANNELS, constant.ATTACHMENTS, constant.ROOT]:
                            new_response = Response()
                            new_response._content = b'{"value": []}'
                            new_response.status_code = 200
                            return new_response
                        else:
                            return {"value": []}
                    elif not (object_type == 'deletion' and response.status_code == 404):
                        self.logger.error(
                            f"Error: {response.reason}. Error while fetching {object_type} from Microsoft Teams, "
                            f"url: {request_url}.")
                    return response
                else:
                    paginate_query = None
                    raise ResponseException(
                        f"Error: {response.reason}. Error while fetching {object_type} from Microsoft Teams, url: "
                        f"{request_url}.")
            except RequestException as exception:
                raise exception
        return response_list

    def get_response_data(self, response):
        """ Get the data from the HTTP response
            :param response: Response from Microsoft Graph API request
        """
        try:
            response_data = response.json()
        except JSONDecodeError as exception:
            self.logger.exception(f"Error while fetching the response data. Error: {exception}")
        return response_data

    def regenerate_token(self, object_type):
        """ Regenerates the access token in case of access token has expired
            :param object_type: Parameter name whether it is teams, channels, channel_chat, channel_docs, calendar,
                user_chats, permissions or deletion
        """
        self.logger.info("Access Token has expired. Regenerating the access token...")
        token = MSALAccessToken(self.logger, self.config)

        # Unable to fetch the CALENDAR and ATTACHMENT using the access token generated via user-password flow
        # So generating the separate access token for fetching CALENDAR and ATTACHMENT objects
        if object_type in [constant.CALENDAR, constant.ATTACHMENTS]:
            self.access_token = token.get_token(is_acquire_for_client=True)
        else:
            self.access_token = token.get_token()
        self.request_header = {
            "Authorization": f"Bearer {self.access_token}"
        }
