import argparse
import logging
import os
from unittest.mock import Mock

from ees_microsoft_teams.configuration import Configuration  # noqa
from ees_microsoft_teams.connector_queue import ConnectorQueue
from ees_microsoft_teams.incremental_sync_command import IncrementalSyncCommand  # noqa

CONFIG_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), "config"),
    "microsoft_teams_connector.yml",
)


def settings():
    """This function loads configuration from the file and returns it along with retry_count setting."""
    configuration = Configuration(file_name=CONFIG_FILE)
    logger = logging.getLogger("unit_test_full_sync_command")
    return configuration, logger


def test_start_producer():
    """Test that start producer process for full sync."""
    # Setup
    args = argparse.Namespace()
    args.name = "dummy"
    args.config_file = CONFIG_FILE
    incremental_sync_obj = IncrementalSyncCommand(args)
    incremental_sync_obj.create_and_execute_jobs = Mock(return_value=[])
    incremental_sync_obj.remove_object_permissions = Mock()
    incremental_sync_obj.create_jobs_for_teams = Mock()
    incremental_sync_obj.create_jobs_for_user_chats = Mock()
    incremental_sync_obj.create_jobs_for_calendars = Mock()
    _, logger = settings()
    queue = ConnectorQueue(logger)

    # Execute
    incremental_sync_obj.start_producer(queue)


def test_start_consumer(caplog):
    """Test that start consumer process for incremental sync."""
    caplog.set_level("INFO")
    args = argparse.Namespace()
    args.name = "dummy"
    args.config_file = CONFIG_FILE
    incremental_sync_obj = IncrementalSyncCommand(args)
    incremental_sync_obj.config._Configuration__configurations["enterprise_search.host_url"] = "https://localhost:9200"
    incremental_sync_obj.create_and_execute_jobs = Mock(return_value=[])
    _, logger = settings()
    queue = ConnectorQueue(logger)
    incremental_sync_obj.start_consumer(queue)
    assert "Completed indexing of the Microsoft Teams objects" in caplog.text
