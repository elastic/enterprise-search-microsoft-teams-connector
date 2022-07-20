#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""schema module contains Connector configuration file schema.
"""
import datetime

from .constant import DATETIME_FORMAT


def coerce_rfc_3339_date(input_date):
    """This function returns true if its argument is a valid RFC 3339 date."""
    if input_date:
        return datetime.datetime.strptime(input_date, DATETIME_FORMAT)
    return False


schema = {
    'username': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'password': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'application_id': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'client_secret': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'tenant_id': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'enterprise_search.api_key': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'enterprise_search.source_id': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'enterprise_search.host_url': {
        'required': True,
        'type': 'string',
        'empty': False
    },
    'enable_document_permission': {
        'required': False,
        'type': 'boolean',
        'default': True
    },
    'object_type_to_index': {
        'type': 'dict',
        'nullable': True,
        'schema': {
            'teams': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'channels': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'channel_messages': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'channel_documents': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'channel_tabs': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'user_chats': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            },
            'calendar': {
                'type': 'dict',
                'nullable': True,
                'schema': {
                    'include_fields': {
                        'nullable': True,
                        'type': 'list'
                    },
                    'exclude_fields': {
                        'nullable': True,
                        'type': 'list'
                    }
                }
            }
        }
    },
    'start_time': {
        'required': False,
        'type': 'datetime',
        'max': datetime.datetime.utcnow(),
        'default': (datetime.datetime.utcnow() - datetime.timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coerce': coerce_rfc_3339_date
    },
    'end_time': {
        'required': False,
        'type': 'datetime',
        'max': datetime.datetime.utcnow(),
        'default': (datetime.datetime.utcnow()).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coerce': coerce_rfc_3339_date
    },
    'log_level': {
        'required': False,
        'type': 'string',
        'default': 'INFO',
        'allowed': ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        'empty': False
    },
    'retry_count': {
        'required': False,
        'type': 'integer',
        'default': 3,
        'min': 1
    },
    'microsoft_teams.user_mapping': {
        'required': False,
        'type': 'string'
    },
    'ms_teams_sync_thread_count': {
        'required': False,
        'type': 'integer',
        'default': 5,
        'min': 1
    },
    'enterprise_search_sync_thread_count': {
        'required': False,
        'type': 'integer',
        'default': 5,
        'min': 1
    }
}
