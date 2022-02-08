# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.


class MSTeamsCalendar():
    """ This class fetches all calendars events from the MS Teams.
    """
    def __init__(self, access_token):
        self.token = access_token

    def get_calendars(self):
        """ This class Fetches all calendars events from MS Teams.
        """
        pass
