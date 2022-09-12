#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains all the constants used throughout the code.
"""

import datetime
import os

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Constants for teams and channels and their children objects
TEAMS = "Teams"
CHANNELS = "Channels"
CHANNEL_MESSAGES = "Channel Messages"
CHANNEL_DOCUMENTS = "Channel Documents"
CHANNEL_TABS = "Channel Tabs"
CHANNEL_DRIVE = "Channel Drive"
CHANNEL_ROOT = "Channel Root"
CHANNEL_DRIVE_ITEM = "Channel Drive Item"
MEMBER = "Member"

# Constants for attachments
ROOT = "Root"
ATTACHMENTS = "Attachments"
DRIVE = "Drive"

# Constants for user chats and its children objects
CHATS = "Chats"
USER_CHATS_MESSAGE = "User Chat Messages"
USER_CHAT_TABS = "User Chat Tabs"
USER_CHAT_DRIVE_ITEM = "User Chat Drive Item"
USER_CHAT_DRIVE = "User Chat Drive"

# Constants for calendar events
USER = "User"
CALENDAR = "Calendar"

# Common Constants
BATCH_SIZE = 100
CONNECTION_TIMEOUT = 60  # Timeout in seconds
MIMETYPES = [
    "audio/aac", "video/x-msvideo", "application/x-cdf", "audio/midi audio/x-midi", "audio/mpeg", "audio/mp4",
    "video/mp4", "video/mpeg", "audio/ogg", "video/ogg", "audio/opus", "audio/wav", "audio/webm", "video/webm",
    "audio/3gpp", "video/3gpp", "video/3gpp2", "audio/3gpp2"]
CURRENT_TIME = (datetime.datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Constants for local storage
LOCAL_STORAGE_DIRECTORY = os.path.join(os.path.dirname(__file__), "doc_ids")
USER_CHAT_DELETION_PATH = os.path.join(LOCAL_STORAGE_DIRECTORY, "microsoft_teams_user_chat_doc_ids.json")
CALENDAR_CHAT_DELETION_PATH = os.path.join(LOCAL_STORAGE_DIRECTORY, "microsoft_teams_calendar_doc_ids.json")
CHANNEL_CHAT_DELETION_PATH = os.path.join(LOCAL_STORAGE_DIRECTORY, "microsoft_teams_channel_chat_doc_ids.json")
