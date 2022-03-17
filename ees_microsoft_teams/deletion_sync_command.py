#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in Microsoft Teams will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""
from .base_command import BaseCommand
from .deletion import start


class DeletionSyncCommand(BaseCommand):
    """This class start execution of deletion feature.
    """
    def execute(self):
        config = self.config
        logger = self.logger
        workplace_search_client = self.workplace_search_client

        start(config, logger, workplace_search_client)
