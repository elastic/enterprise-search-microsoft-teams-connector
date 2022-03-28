#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
"""This module allows to remove recently deleted documents from Elastic Enterprise Search.

    Documents that were deleted in Microsoft Teams will still be available in
    Elastic Enterprise Search until a full sync happens, or until this module is used.
"""


class Deletion:
    """ This class is used to remove document from the workplace search
    """
    pass
