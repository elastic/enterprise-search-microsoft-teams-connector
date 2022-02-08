# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import os
import datetime

HOSTNAME = "https://login.microsoftonline.com/"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
CONFIG_FILE = "ms_teams_config.yml"
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), '../checkpoint.json')
TEAMS = "Teams"
CHANNELS = "Channels"
CHANNEL_MESSAGES = "Channel Messages"
CHANNEL_DOCUMENTS = "Channel Documents"
CHANNEL_ATTACHMENTS = "Channel Attachments"
CHANNEL_MEETINGS = "Channel Meetings"
CHANNEL_TABS = "Channel Tabs"
CHANNEL_DRIVE = "Channel Drive"
CHANNEL_ROOT = "Channel Root"
CHANNEL_DRIVE_ITEM = "Channel Drive Item"
ROOT = "Root"
ATTACHMENTS = "Attachments"
DRIVE = "Drive"
MEMBER = "Member"
USER_CHATS_MESSAGE = "User Chats Message"
USER_CHAT_TABS = "User Chat Tabs"
MEETING_RECORDING = "Meeting Recording"
MEETING = "Meeting"
CALENDAR = "Calendar"
CHATS = "Chats"
USER_CHAT_ATTACHMENT = "User Chats Attachment"
USER_CHAT_DRIVE_ITEM = "User Chat Drive Item"
USER_CHAT_DRIVE = "User Chat Drive"
USER = "User"
MIMETYPES = ["audio/aac", "video/x-msvideo", "application/x-cdf", "audio/midi audio/x-midi", "audio/mpeg", "audio/mp4", "video/mp4", "video/mpeg", "audio/ogg", "video/ogg", "audio/opus", "audio/wav", "audio/webm", "video/webm", "audio/3gpp", "video/3gpp", "video/3gpp2", "audio/3gpp2"]
SCOPE = ["User.Read.All", "TeamMember.Read.All", "ChannelMessage.Read.All", "Chat.Read", "Chat.ReadBasic", "Calendars.Read"]
CLIENT_SCOPE = "https://graph.microsoft.com/.default"
DOCUMENT_LIMIT = 100
CURRENT_TIME = (datetime.datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
USER_CHAT_DEINDEXING_PATH = os.path.join(os.path.abspath("..."), "doc_ids", "ms_teams_user_chat_doc_ids.json")
CALENDAR_CHAT_DEINDEXING_PATH = os.path.join(os.path.abspath("..."), "doc_ids", "ms_teams_calendar_doc_ids.json")
CHANNEL_CHAT_DEINDEXING_PATH = os.path.join(os.path.abspath("..."), "doc_ids", "ms_teams_channel_chat_doc_ids.json")
MAX_DELETED_DOCUMENT = 100
MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
USER_MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
