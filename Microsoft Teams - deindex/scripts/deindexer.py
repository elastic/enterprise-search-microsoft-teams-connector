# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import time
import multiprocessing
import src.logger_manager as log
from datetime import datetime
from src.base_class import BaseClass
from src.adapter import DEFAULT_SCHEMA
from src.ms_teams_user_messages import MSTeamsUserMessage
from src.ms_teams_channels import MSTeamsChannels
from src.msal_access_token import MSALAccessToken
from src.checkpointing import Checkpoint
from src.configuration import Configuration
from src.ms_teams_calendars import MSTeamsCalendar
from src.utils import print_and_log
from src import constant

logger = log.setup_logging("ms_teams_deindex")


class Deindexer(BaseClass):
    """ This class is used to remove document from the workplace search
    """

    def __init__(self, token):
        BaseClass.__init__(self, logger=logger)
        self.objects = self.configurations.get("objects")
        self.checkpoint = Checkpoint(logger)
        self.access_token = token

    def get_schema_fields(self, document_name):
        """ returns the schema of all the include_fields or exclude_fields specified in the configuration file.
            :param document_name: Document name from Teams, Channels, Channel Messages, User Chats, etc.
            Returns:
                schema: Included and excluded fields schema
        """
        fields = self.objects.get(document_name)
        adapter_schema = DEFAULT_SCHEMA[document_name]
        field_id = adapter_schema['id']
        if fields:
            include_fields = fields.get("include_fields")
            exclude_fields = fields.get("exclude_fields")
            if include_fields:
                adapter_schema = {
                    key: val for key, val in adapter_schema.items() if val in include_fields}
            elif exclude_fields:
                adapter_schema = {
                    key: val for key, val in adapter_schema.items() if val not in exclude_fields}
            adapter_schema['id'] = field_id
        return adapter_schema

    def delete_document(self, final_deleted_list):
        """This method will delete all the documents of specified ids from workplace search
           :param final_deleted_list: list of ids
        """
        step = constant.MAX_DELETED_DOCUMENT
        for index in range(0, len(final_deleted_list), constant.MAX_DELETED_DOCUMENT):
            final_list = final_deleted_list[index:index + step]
            try:
                # Logic to delete documents from the workplace search
                self.ws_client.delete_documents(
                    http_auth=self.ws_token,
                    content_source_id=self.ws_source,
                    document_ids=final_list)
            except Exception as exception:
                self.logger.exception(f"Error while deleting the documents to the workplace. Error: {exception}")
                return []

    def deindexing_teams(self):
        """ The purpose of this method is to delete the teams related documents from the workplace search.
        """
        indexed_teams = []
        delete_keys_documents = []
        global_keys_documents = []
        doc_id_data = {"global_keys": [], "delete_keys": []}

        logger.info(f"Started deindexing process of teams and it's objects on {datetime.now()}")

        if (os.path.exists(constant.CHANNEL_CHAT_DEINDEXING_PATH) and os.path.getsize(constant.CHANNEL_CHAT_DEINDEXING_PATH) > 0):
            with open(constant.CHANNEL_CHAT_DEINDEXING_PATH, encoding="UTF-8") as ids_store:
                try:
                    indexed_teams = json.load(ids_store)
                    indexed_teams["delete_keys"] = indexed_teams.get("delete_keys") or []
                    indexed_teams["global_keys"] = indexed_teams.get("global_keys") or []
                    global_keys_documents = indexed_teams.get("global_keys")
                except ValueError as exception:
                    logger.exception(
                        "Error while reading teams data from the path: %s. Error: %s"
                        % (constant.CHANNEL_CHAT_DEINDEXING_PATH, exception)
                    )

                # Fetching start datetime from the YML file becuase we have to we have to fetch all data and check respective document exists or not instead of calling individual to improve performance
                start_time = self.configurations.get("start_time")
                deleted_data = indexed_teams["delete_keys"]

                # Logic to fetch all teams and channel details of microsoft team
                teams_channels_obj = MSTeamsChannels(self.access_token, start_time, constant.CURRENT_TIME, self.get_schema_fields, logger)
                teams, _ = teams_channels_obj.get_all_teams([])
                channels, channel_doc, _ = teams_channels_obj.get_team_channels(teams, [])
                channel_msgs, _ = teams_channels_obj.get_channel_messages(channels, [])
                channel_tabs, _ = teams_channels_obj.get_channel_tabs(channels, [])
                channel_documents, _ = teams_channels_obj.get_channel_documents(teams, [])

                live_data = []
                live_data.extend(teams)
                live_data.extend(channel_doc)
                live_data.extend(channel_msgs)
                live_data.extend(channel_tabs)
                live_data.extend(channel_documents)

                self.iterate_item_ntimes(live_data, deleted_data, delete_keys_documents, global_keys_documents, "", "")
                final_deleted_list = list(delete_keys_documents)
                self.delete_document(final_deleted_list)

                # Logic to update the ms_teams_channel_chat_doc_ids.json file with latest data
                doc_id_data["global_keys"] = list(global_keys_documents)
                with open(constant.CHANNEL_CHAT_DEINDEXING_PATH, "w", encoding="UTF-8") as f:
                    try:
                        json.dump(doc_id_data, f, indent=4)
                    except ValueError as exception:
                        logger.exception('Error while adding ids to json file. Error: %s' % (exception))
        else:
            logger.info("No records are present to check for deindexing teams and it's objects")
        logger.info(f"Completed deindexing process of teams and it's objects on {datetime.now()}")

    def deindexing_user_chat(self):
        """ The purpose of this method is to delete the user chat related documents from the workplace search.
        """
        indexed_user_chat = []
        delete_keys_documents = []
        global_keys_documents = []
        storage_with_collection = {"global_keys": [], "delete_keys": []}
        logger.info(f"Started deindexing process of user chat on {datetime.now()}")
        # Logic to read indexed documents from the ms_teams_user_chat_doc_ids.json file
        if (os.path.exists(constant.USER_CHAT_DEINDEXING_PATH) and os.path.getsize(constant.USER_CHAT_DEINDEXING_PATH) > 0):
            try:
                with open(constant.USER_CHAT_DEINDEXING_PATH) as ids_store:
                    try:
                        indexed_user_chat = json.load(ids_store)
                        indexed_user_chat["delete_keys"] = indexed_user_chat.get("delete_keys") or []
                        indexed_user_chat["global_keys"] = indexed_user_chat.get("global_keys") or []
                        global_keys_documents = indexed_user_chat.get("global_keys")
                    except ValueError as exception:
                        logger.exception(
                            "Error while reading users chats data from the path: %s. Error: %s"
                            % (constant.USER_CHAT_DEINDEXING_PATH, exception)
                        )
                    # Fetching start datetime from them the YML file becuase we have to we have to fetch all data and check respective document exists or not instead of calling individual to improve performance
                    start_time = self.configurations.get("start_time")
                    # Logic to fetch all chats details of microsoft team
                    user_msg = MSTeamsUserMessage(self.access_token, start_time, constant.CURRENT_TIME, self.get_schema_fields, logger)
                    _, live_documents, _ = user_msg.get_chats([], {})
                    docids_data = indexed_user_chat["delete_keys"]
                    # Logic to iterate each items based on prent and child relationship and insert items into global variable for deindexing
                    self.iterate_item_ntimes(live_documents, docids_data, delete_keys_documents, global_keys_documents, "", "")
                    final_deleted_list = list(delete_keys_documents)
                    self.delete_document(final_deleted_list)
                    storage_with_collection["global_keys"] = list(global_keys_documents)
                    with open(constant.USER_CHAT_DEINDEXING_PATH, "w") as f:
                        try:
                            json.dump(storage_with_collection, f, indent=4)
                        except ValueError as exception:
                            logger.warn('Error while adding ids to json file. Error: %s' % (exception))
            except Exception as exception:
                print_and_log(
                    logger,
                    "exception",
                    "[Fail] Error while deindexing user chats details into workplace search. Error: %s"
                    % (
                        exception,
                    ),
                )
        else:
            logger.info("No records are present to check for deindexing user chats")
        logger.info(f"Completed deindexing process of user chat on {datetime.now()}")

    def deindexing_calendar_chat(self):
        """ The purpose of this method is to delete the calendar related documents from the workplace search.
        """
        indexed_calendars = []
        delete_keys_documents = []
        global_keys_documents = []
        doc_id_data = {"global_keys": [], "delete_keys": []}

        logger.info(f"Started deindexing process of calendars on {datetime.now()}")
        if (os.path.exists(constant.CALENDAR_CHAT_DEINDEXING_PATH) and os.path.getsize(constant.CALENDAR_CHAT_DEINDEXING_PATH) > 0):
            with open(constant.CALENDAR_CHAT_DEINDEXING_PATH, encoding="UTF-8") as ids_store:
                try:
                    indexed_calendars = json.load(ids_store)
                    indexed_calendars["delete_keys"] = indexed_calendars.get("delete_keys") or []
                    indexed_calendars["global_keys"] = indexed_calendars.get("global_keys") or []
                    global_keys_documents = indexed_calendars.get("global_keys")
                except ValueError as exception:
                    logger.exception(
                        "Error while reading calendars data from the path: %s. Error: %s"
                        % (constant.CALENDAR_CHAT_DEINDEXING_PATH, exception)
                    )

                # Fetching start datetime from them the YML file becuase we have to we have to fetch all data and check respective document exists or not instead of calling individual to improve performance
                start_time = self.configurations.get("start_time")
                deleted_data = indexed_calendars["delete_keys"]

                # Logic to fetch all chats details of microsoft team
                calendars = MSTeamsCalendar(self.access_token, start_time, constant.CURRENT_TIME, self.get_schema_fields, logger)
                _, documents, is_error = calendars.get_calendars([])
                self.iterate_item_ntimes(documents, deleted_data, delete_keys_documents, global_keys_documents, "", "")
                final_deleted_list = list(delete_keys_documents)
                self.delete_document(final_deleted_list)
                # Logic to update the ms_teams_user_chat_doc_ids.json file with latest data
                doc_id_data["global_keys"] = list(global_keys_documents)
                with open(constant.CALENDAR_CHAT_DEINDEXING_PATH, "w", encoding="UTF-8") as f:
                    try:
                        json.dump(doc_id_data, f, indent=4)
                    except ValueError as exception:
                        logger.exception('Error while adding ids to json file. Error: %s' % (exception))
        else:
            logger.info("No records are present to check for deindexing calendars")
        logger.info(f"Completed deindexing process of calendars on {datetime.now()}")

    def iterate_item_ntimes(self, live_documents, doc_ids_documents, deleted_documents, global_keys_documents, parent_id, super_parent_id):
        """ The purpose of this method is to recursively iterate documents upto N level for deindexing.
            :param live_documents: Pass all documents received from user chat
            :param doc_ids_documents: Pass all documents which is availabe inside ms_teams_user_chat_doc_ids.json file
            :param deleted_documents: Pass global variable to store deleted documents
            :param global_keys_documents: Pass global varibale of global_keys to removed deleted data
            :param parent_id: Pass parent id of first document to start the execution
            :param super_parent_id: Pass super parent id of first document to start the execution
        """
        parent_items = list(filter(lambda seq: self.get_child_items(seq, parent_id), doc_ids_documents))
        for item in parent_items:
            id = item["id"]
            parent_id = item["parent_id"]
            super_parent_id = item["super_parent_id"]
            type = item["type"]
            items_exists = list(filter(
                lambda seq: self.check_item_isexists_in_livedata(seq, id), live_documents))
            if(len(items_exists) == 0 and type not in [constant.CHATS, constant.USER, constant.USER_CHAT_DRIVE, constant.USER_CHAT_DRIVE_ITEM, constant.CHANNEL_DRIVE, constant.CHANNEL_ROOT, constant.CHANNEL_DRIVE_ITEM]):
                deleted_documents.append(id)
                if item in global_keys_documents:
                    global_keys_documents.remove(item)

            # Logic to recursively call same function till the N number of child level.
            self.iterate_item_ntimes(live_documents, doc_ids_documents,
                                     deleted_documents, global_keys_documents, id, super_parent_id)

    def get_child_items(self, document_item, parent_id):
        """ The purpose of this method is to filter child item while iterating each document.
            :param document_item: Pass user chat document
            :param parent_id: Pass parent id of user chat document
        """
        return document_item["parent_id"] == parent_id

    def check_item_isexists_in_livedata(self, document_item, id):
        """ The purpose of this method is to filter item from the live data.
            :param document_item: Pass user chat document
            :param parent_id: Pass id of user chat document
        """
        return document_item["id"] == id


def start_multiprocessing(job_name, access_token):
    """This function is used for initiating the multiprocessing for the jobs
       :param job_name: Pass the type of object
       :param access_token: ms teams access token
    """
    deindexer = Deindexer(access_token)
    if job_name == "teams":
        deindexer.deindexing_teams()
    if job_name == "user_chats":
        deindexer.deindexing_user_chat()
    if job_name == "calendar":
        deindexer.deindexing_calendar_chat()


def start():
    """ The purpose of this method is to delete document from the workplace search when it will be deleted from the microsoft teams
        and this class run three different process parallelly to delete document from the workplace search. One for User Chat, second for Channel Chat and third for Calendar.
    """

    logger.info("Starting the deindexing...")
    data = Configuration(logger).configurations
    objects = data.get("objects")
    # Logic to generate access token to connect microsoft graph api to fetch data.
    token = MSALAccessToken(logger)
    obj_permissions_list = ["teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]
    while True:
        # The purpose of this code is to create multiple process job.
        deindexing_processes = []
        access_token = token.get_token()
        if any(obj in objects for obj in obj_permissions_list):
            p1 = multiprocessing.Process(target=start_multiprocessing, args=("teams", access_token,))
            deindexing_processes.append(p1)
        if "user_chats" in objects:
            p2 = multiprocessing.Process(target=start_multiprocessing, args=("user_chats", access_token,))
            deindexing_processes.append(p2)
        if "calendar" in objects:
            calendar_access_token = token.get_token(is_aquire_for_client=True)
            p3 = multiprocessing.Process(target=start_multiprocessing, args=("calendar", calendar_access_token,))
            deindexing_processes.append(p3)

        # Logic to start the each job and run parallelly.
        for pro_item in deindexing_processes:
            pro_item.start()
        for pro_item in deindexing_processes:
            pro_item.join()

        interval = data.get("deletion_interval")
        # TODO: need to use schedule instead of time.sleep
        logger.info("Sleeping..")
        time.sleep(interval * 60)


if __name__ == "__main__":
    start()
