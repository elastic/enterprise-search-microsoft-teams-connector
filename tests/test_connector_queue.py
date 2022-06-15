#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import logging
import os
import sys

from ees_microsoft_teams.connector_queue import ConnectorQueue  # noqa

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logger = logging.getLogger("unit_test_connector_queue")


def test_end_signal():
    """Tests that the end signal is sent to the queue to notify it to stop listening for new incoming data"""
    expected_message = {"type": "signal_close"}
    queue = ConnectorQueue(logger)
    queue.put("Example data")
    queue.end_signal()
    queue.get()
    source_message = queue.get()
    assert source_message == expected_message


def test_put_checkpoint():
    """Tests putting the checkpoint object in the queue which will be used by the consumer to update the checkpoint file"""
    expected_message = {'type': 'checkpoint', 'checkpoint_time': '2022-05-24T14:11:14Z', 'indexing_type': 'full',
                        'object_type': 'key'}
    queue = ConnectorQueue(logger)

    queue.put("Example data")
    queue.put_checkpoint("key", '2022-05-24T14:11:14Z', "full")
    queue.end_signal()

    queue.get()
    source_message = queue.get()
    queue.get()
    assert source_message == expected_message


def test_append_to_queue():
    """Tests that the append data in queue"""
    data = []
    for count in range(10):
        data.append(count)
    expected_message = {"type": "document_list", "data": data}
    queue = ConnectorQueue(logger)
    queue.append_to_queue("document_list", data)
    queue.end_signal()
    current_message = queue.get()
    queue.get()
    assert current_message == expected_message
