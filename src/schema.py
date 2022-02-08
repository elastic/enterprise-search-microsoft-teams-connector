# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import datetime


def validate_date_new(input_date):
    """ Validates the user given datetime
        :param input_date: Start_time or end_time from configuration file
    """
    if input_date:
        return datetime.datetime.strptime(input_date, "%Y-%m-%dT%H:%M:%SZ")


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
    'enterprise_search.access_token': {
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
    'objects': {
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
        'coerce': validate_date_new
    },
    'end_time': {
        'required': False,
        'type': 'datetime',
        'max': datetime.datetime.utcnow(),
        'default': (datetime.datetime.utcnow()).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'coerce': validate_date_new
    },
    'indexing_interval': {
        'required': False,
        'type': 'integer',
        'default': 60,
        'min': 1
    },
    'full_sync_interval': {
        'required': False,
        'type': 'integer',
        'default': 2880,
        'min': 1
    },
    'deletion_interval': {
        'required': False,
        'type': 'integer',
        'default': 60,
        'min': 1
    },
    'log_level': {
        'required': False,
        'type': 'string',
        'default': 'info',
        'allowed': ['debug', 'info', 'warn', 'error'],
        'empty': False
    },
    'retry_count': {
        'required': False,
        'type': 'integer',
        'default': 3,
        'min': 1
    },
    'msteams_workplace_user_mapping': {
        'required': False,
        'type': 'string'
    },
    'worker_process': {
        'required': False,
        'type': 'integer',
        'default': 40,
        'min': 1
    }
}
