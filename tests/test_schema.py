#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import datetime  # noqa

from ees_microsoft_teams import schema  # noqa


def test_coerce_rfc_3339_date():
    """This function convert a string date time into datetime format"""

    # Setup
    input_date = "2021-12-28T15:14:28Z"

    # Execute
    source_date = schema.coerce_rfc_3339_date(input_date)

    # Assert
    assert source_date == datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")
