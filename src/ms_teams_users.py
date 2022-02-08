# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import requests
import json
from src import constant


class MSTeamsUsers:
    """ This class is used to fetch all MS Teams users.
    """
    def __init__(self, token, logger):
        self.access_token = token
        self.logger = logger

    def get_all_users(self):
        """ This method fetched all MS Teams users.
        Returns:
            user_details: List of dictionaries containing user details.
        """
        user_details = []
        request_header = {
            "Authorization": f"Bearer {self.access_token}"
        }
        try:
            user_response = requests.get(f'{constant.GRAPH_BASE_URL}/users', headers=request_header)
            if user_response and user_response.status_code == requests.codes.ok:
                user_response_data = json.loads(user_response.text)
                for user in user_response_data["value"]:
                    user_data = {}
                    if user['mail']:
                        user_data['mail'] = user['mail']
                        user_data["userId"] = user["id"]
                        user_data["displayName"] = user["displayName"]
                        user_data["mailAddress"] = user["userPrincipalName"]
                        user_details.append(user_data)
            else:
                self.logger.error("Error while fetching users from Azure Platform")
        except Exception as exception:
            self.logger.exception(exception)
        return user_details
