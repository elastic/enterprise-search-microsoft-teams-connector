# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.


class MSTeamsUserMessage():
    """ This class fetches chat messages from the MS Teams.
    """

    def __init__(self, token):
        self.access_token = token

    def get_user_messages(self):
        """ This method is used to fetch the chat messages from the MS Teams.
        """
        pass
