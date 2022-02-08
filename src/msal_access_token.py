# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

from msal import ConfidentialClientApplication
from src.base_class import BaseClass
from src.constant import HOSTNAME, SCOPE, CLIENT_SCOPE


class MSALAccessToken(BaseClass):
    """ This class is used to generate the access token to call the MS Graph APIs.
    """
    def __init__(self, logger):
        self.logger = logger
        BaseClass.__init__(self, logger=logger)

    def get_token(self, is_aquire_for_client=False):
        """ Generates the access token to call MS Graph APIs
            :param is_aquire_for_client: Pass True if want to acquire token by using client_id, tenant_id and secret_key
        Returns:
            access_token: Access token for authorization
        """
        self.logger.info(f"Generating the access token for the tenant ID: {self.tenant_id}...")
        authority = f"{HOSTNAME}{self.tenant_id}"

        try:
            auth_context = ConfidentialClientApplication(self.client_id, client_credential=self.client_secret, authority=authority)
            if is_aquire_for_client:
                token = auth_context.acquire_token_for_client(CLIENT_SCOPE)
            else:
                token = auth_context.acquire_token_by_username_password(self.username, self.password, SCOPE)
            if not token.get("access_token"):
                self.logger.error("Could not generate the access token, please verify the MS Teams configuration settings in configuration file.")
                exit(0)
            self.logger.info("Successfully generated the access token.")
            return token.get("access_token")
        except Exception as exception:
            self.logger.exception(f"Error while generating the access token. Error: {exception}")
            exit(0)
