#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Module containing default schema for data uploaded to Enterprise Search.

    This module contains definition of default schema for the data
    that will be uploaded to Elastic Enterprise Search per each Microsoft Teams object.

    Keys for each object represent the fields that will be uploaded to Enterprise Search
    while key values represent Microsoft Teams fields that will be used to populate the data.
"""

DEFAULT_SCHEMA = {
    'teams': {
        'id': 'id',
        'title': 'displayName',
        'body': 'description',
        'created_at': 'createdDateTime'
    },
    'channels': {
        'id': 'id',
        'url': 'webUrl',
        'title': 'displayName',
        'body': 'description',
        'created_at': 'createdDateTime'
    },
    'channel_messages': {
        'id': 'id',
        'url': 'webUrl',
        'last_updated': 'lastModifiedDateTime',
        'created_at': 'createdDateTime'
    },
    'channel_documents': {
        'id': 'id',
        'title': 'name',
        'last_updated': 'lastModifiedDateTime',
        'created_at': 'createdDateTime',
        'url': 'webUrl'
    },
    'channel_tabs': {
        'id': 'id',
        'title': 'displayName',
        'url': 'webUrl'
    },
    'user_chats': {
        'id': 'id',
        'last_updated': 'lastModifiedDateTime',
        'created_at': 'createdDateTime'
    },
    'calendar': {
        'id': 'id',
        'last_updated': 'lastModifiedDateTime',
        'title': 'subject',
        'created_at': 'createdDateTime'
    },
    'user_tabs': {
        'id': 'id',
        'title': 'displayName'
    }
}
