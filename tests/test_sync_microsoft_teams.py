#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.connector_queue import ConnectorQueue  # noqa
from ees_microsoft_teams.sync_microsoft_teams import SyncMicrosoftTeams  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)

USER_MAPPING = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "user_mapping.csv",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(
        file_name=CONFIG_FILE
    )

    logger = logging.getLogger("unit_test_permission")
    return configuration, logger


def create_object_of_sync_microsoft_teams():
    """This function create object of Sync Microsoft Teams class.
    """
    configs, logger = settings()
    queue = ConnectorQueue(logger)
    return SyncMicrosoftTeams('full', configs, logger, queue)


def test_add_permissions_to_queue():
    """ Add the permissions to a queue.
    """
    permission_sync_obj = create_object_of_sync_microsoft_teams()
    permission_sync_obj.add_permissions_to_queue("dummy_user", ["permission1"])
    size = permission_sync_obj.queue.qsize()
    assert size == 1
