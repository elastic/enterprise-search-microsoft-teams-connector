#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
""" This module is used to generate the access token required to authenticate the
    Microsoft Graph APIs.
"""

from msal import ConfidentialClientApplication

SCOPE = ["User.Read.All", "TeamMember.Read.All", "ChannelMessage.Read.All",
         "Chat.Read", "Chat.ReadBasic", "Calendars.Read"]


class AccesstokenError(Exception):
    """Exception raised when there is an error in generating access token.
    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class MSALAccessToken:
    """This class generates and returns the access token."""

    def __init__(self, logger, configs):
        self.logger = logger
        self.config = configs
        self.logger.info("Initializing the Token generation")

    def get_token(self, is_acquire_for_client=False):
        """ Generates the access token to call Microsoft Graph APIs
            :param is_acquire_for_client: Pass True if want to acquire token by using client_id, tenant_id and
                secret_key
        Returns:
            access_token: Access token for authorization
        """
        self.logger.info(f'Generating the access token for the tenant ID: {self.config.get_value("tenant_id")}...')
        authority = f'https://login.microsoftonline.com/{self.config.get_value("tenant_id")}'

        try:
            auth_context = ConfidentialClientApplication(
                self.config.get_value("application_id"),
                client_credential=self.config.get_value("client_secret"),
                authority=authority)
            if is_acquire_for_client:
                token = auth_context.acquire_token_for_client("https://graph.microsoft.com/.default")
            else:
                token = auth_context.acquire_token_by_username_password(
                    self.config.get_value("username"), self.config.get_value("password"), SCOPE)
            if not token.get("access_token"):
                raise AccesstokenError(
                    "Could not generate the access token, please verify the Microsoft Teams configuration settings in \
                        configuration file.")
            self.logger.info("Successfully generated the access token.")
            return token.get("access_token")
        except Exception as exception:
            raise AccesstokenError(f"Error while generating the access token. Error: {exception}")
