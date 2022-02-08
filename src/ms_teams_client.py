# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import requests
import time
import pandas
import src.constant as constant
from requests.exceptions import RequestException
from src.msal_access_token import MSALAccessToken
from json import JSONDecodeError
from src.base_class import BaseClass
from src.utils import print_and_log


class MSTeamsClient(BaseClass):
    def __init__(self, logger, access_token):
        BaseClass.__init__(self, logger=logger)
        self.access_token = access_token
        self.logger = logger
        self.request_header = {
            "Authorization": f"Bearer {self.access_token}"
        }

    def get(self, url, object_type, is_pagination, is_filter, is_pandas_series=False, page_size=0, filter_query="", datetime_filter_column_name="lastModifiedDateTime"):
        """ Invokes a GET call to the MS Graph API
            :param url: Base url to call the Graph API
            :param object_type: Parameter name whether it is teams, channels, channel_chat, channel_docs, calendar, user_chats, permissions or deindex
            :param is_pagination: Flag to check if pagination is enabled
            :param is_filter: Flag to check if filter is enabled
            :param is_pandas_series: Flag to check if pandas series is enabled
            :param page_size: Size of the top variable for pagination
            :param filter_query: Filter query if filter is enabled
            :param datetime_filter_column_name: Filter query if is_pandas_series enabled
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
                if object_type != constant.CHANNELS:
                    start_time = filter_query.split("/")[0]
                    end_time = filter_query.split("/")[1]
                paginate_query = " "

            request_url = f"{url}{paginate_query.strip()}"
            flag = False
            retry = 0
            while retry <= self.retry_count:
                try:
                    response = requests.get(
                        request_url,
                        headers=self.request_header
                    )
                    if response and response.status_code == requests.codes.ok:
                        if is_pagination and not is_filter:
                            response_data = self.get_response_data(response)
                            if object_type in [constant.MEMBER, constant.TEAMS, constant.CHATS, constant.DRIVE, constant.CALENDAR]:
                                response_list["value"].extend(response_data.get("value"))
                            else:
                                data_frame = pandas.DataFrame(response_data.get("value"))
                                if not data_frame.empty:
                                    data_frame.lastModifiedDateTime = pandas.to_datetime(data_frame.lastModifiedDateTime)
                                    filtered_df = data_frame.loc[(data_frame['lastModifiedDateTime'] >= start_time) & (data_frame['lastModifiedDateTime'] < end_time)]
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
                        elif not (object_type in [constant.CHANNELS, constant.CHANNEL_TABS, constant.ROOT, constant.ATTACHMENTS] or is_pagination or is_filter):
                            response_data = self.get_response_data(response)
                            data_frame = pandas.DataFrame(response_data.get("value"))
                            if not data_frame.empty:
                                rows = data_frame
                                if is_pandas_series:
                                    rows = data_frame.configuration.apply(pandas.Series)
                                rows[datetime_filter_column_name] = pandas.to_datetime(rows[datetime_filter_column_name])
                                filtered_df = data_frame.loc[(rows[datetime_filter_column_name] >= start_time) & (rows[datetime_filter_column_name] < end_time)]
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
                        response_data = self.get_response_data(response)
                        # Error 403 occurs when the current user is trying fetch the Teams and it's object which was created by other user
                        if response.status_code == 403 or (response.status_code == 404 and response_data.get("error", {}).get("code") == "NotFound"):
                            pass
                        elif not (object_type == 'deindex' and response.status_code == 404):
                            print_and_log(
                                self.logger,
                                "error",
                                f"Error: {response.reason}. Error while fetching {object_type} from MS Teams, url: {request_url}."
                            )
                        return response
                    else:
                        print_and_log(
                            self.logger,
                            "error",
                            f"Error: {response.reason}. Error while fetching {object_type} from MS Teams, url: {request_url}. Retry Count: {retry}."
                        )
                        # This condition is to avoid sleeping for the last time
                        if retry < self.retry_count:
                            time.sleep(2 ** retry)
                        else:
                            return response
                        retry += 1
                        paginate_query = None
                except RequestException as exception:
                    print_and_log(
                        self.logger,
                        "exception",
                        f"Error: {exception}. Error while fetching {object_type} from MS Teams, url: {request_url}. Retry Count: {retry}."
                    )
                    # This condition is to avoid sleeping for the last time
                    if retry < self.retry_count:
                        time.sleep(2 ** retry)
                    else:
                        return False
                    retry += 1
        return response_list

    def get_response_data(self, response):
        """ This function is used to get the data from response
            :param response: Response from MS Graph API request
        """
        try:
            response_data = response.json()
        except JSONDecodeError as exception:
            self.logger.exception(f"Error while fetching the response data. Error: {exception}")
        return response_data

    def regenerate_token(self, object_type):
        """ This function is used to regenrate the access token in case of access token has expired
            :param object_type: Parameter name whether it is teams, channels, channel_chat, channel_docs, calendar, user_chats, permissions or deindex
        """
        self.logger.info("Access Token has expired. Regenerating the access token...")
        token = MSALAccessToken(self.logger)
        if object_type in [constant.CALENDAR, constant.ATTACHMENTS]:
            self.access_token = token.get_token(is_aquire_for_client=True)
        else:
            self.access_token = token.get_token()
        self.request_header = {
            "Authorization": f"Bearer {self.access_token}"
        }
