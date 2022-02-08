# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import copy
import csv
import time
import json
import multiprocessing
import pandas as pd
import src.logger_manager as log
import src.constant as constant
from datetime import datetime
from src.msal_access_token import MSALAccessToken
from src.ms_teams_channels import MSTeamsChannels
from src.checkpointing import Checkpoint
from src.configuration import Configuration
from src.usergroup_permissions import UserGroupPermissions
from src.base_class import BaseClass
from src import ms_teams_user_messages as ms_msg
from src import ms_teams_calendars as cal
from src.adapter import DEFAULT_SCHEMA
from src.utils import print_and_log

logger = log.setup_logging("ms_teams_index")


class Indexer(BaseClass):
    """ This class is responsible for indexing the MS Teams objects and it's permissions to the Workplace Search.
    """

    def __init__(self, access_token, start_time, end_time):
        BaseClass.__init__(self, logger=logger)
        self.access_token = access_token
        self.is_error = False
        self.start_time = start_time
        self.end_time = end_time

    def get_schema_fields(self, document_name):
        """ Returns the schema of all the include_fields or exclude_fields specified in the configuration file.
            :param document_name: Document name from teams, channels, channel_messages, channel_tabs, channel_documents, calendar and user_chats
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
                adapter_schema = {key: val for key, val in adapter_schema.items() if val in include_fields}
            elif exclude_fields:
                adapter_schema = {key: val for key, val in adapter_schema.items() if val not in exclude_fields}
            adapter_schema['id'] = field_id
        return adapter_schema

    def get_records_by_types(self, document):
        """This method is used to for grouping the document based on their type
           :param document: Document to be indexed
           Returns:
                df_dict: dictonary of type with its count
        """
        df = pd.DataFrame(document)
        df_size = df.groupby('type').size()
        df_dict = df_size.to_dict()
        return df_dict

    def filter_removed_item_by_id(self, item, id):
        """This method is used filter removed document by id
           :param item: Pass document
           :param id: Pass id of the document which having error from workplace search
        """
        return item["id"] == id

    def bulk_index_document(self, document, param_name):
        """ This method indexes the documents to the workplace.
            :param document: Document to be indexed
            :param success_message: Success message
            :param failure_message: Failure message while indexing the document
            :param param_name: Parameter name
        """
        try:
            document_list = []
            if document:
                total_records_dict = self.get_records_by_types(document)
                self.logger.info(f"Indexing the {param_name} documents to the Workplace Search...")
                document_list = [document[i * constant.DOCUMENT_LIMIT:(i + 1) * constant.DOCUMENT_LIMIT] for i in range((len(document) + constant.DOCUMENT_LIMIT - 1) // constant.DOCUMENT_LIMIT)]
                for chunk in document_list:
                    response = self.ws_client.index_documents(
                        content_source_id=self.ws_source,
                        documents=chunk
                    )
                    for each in response['results']:
                        if each['errors']:
                            item = list(filter(lambda seq: self.filter_removed_item_by_id(seq, each['id']), document))
                            document.remove(item[0])
                            logger.error(f"Error while indexing {each['id']}. Error: {each['errors']}")
                total_inserted_record_dict = self.get_records_by_types(document)
                for type, count in total_records_dict.items():
                    self.logger.info(f"Total {total_inserted_record_dict[type]} {type} indexed out of {count}.")
            else:
                self.logger.info(f"{param_name} are up-to-date to the worplace.")
            self.logger.info(f"Successfully indexed the {param_name} to the workplace")

        except Exception as exception:
            self.logger.exception(f"Error while indexing the {param_name} to the workplace. Error: {exception}")
            self.is_error = True

    def workplace_add_permission(self, user_name, permissions):
        """ This method used to index the user permissions into Workplace Search
            for the user in paramter user_name
            :param user_name: A string value denoting the username of the user
            :param permission: Permission that needs to be provided to the user
        """
        try:
            self.ws_client.put_user_permissions(
                content_source_id=self.ws_source,
                user=user_name,
                body={
                    "permissions": permissions
                },
            )
            self.logger.info(f"Successfully indexed the permissions for user {user_name} to the workplace")
        except Exception as exception:
            self.logger.exception(f"Error while indexing the permissions for user:{user_name} to the workplace. Error: {exception}")
            self.is_error = True
            return []

    def index_permissions(self, user, roles):
        """ This method is used to map the ms teams users to workplace search
            users and responsible to call the user permissions indexer method
            :param users: Users for indexing the permissions
            :param roles: User roles
        """
        rows = {}
        if (self.mapping_sheet_path and os.path.exists(self.mapping_sheet_path) and os.path.getsize(self.mapping_sheet_path) > 0):
            with open(self.mapping_sheet_path, encoding="UTF-8") as file:
                csvreader = csv.reader(file)
                for row in csvreader:
                    rows[row[0]] = row[1]
        user_name = rows.get(user, user)
        self.workplace_add_permission(user_name, roles)

    def index_calendar(self, is_error_shared):
        """ This method is used to index the user calendar events into Workplace Search.
            :param indexing_type: Type of indexing (full sync or incremental)
        """
        logger.info("Start fetching and indexing the calendars...")
        storage_with_collection = {"global_keys": [], "delete_keys": []}
        ids_collection = {}
        doc_ids_storage = []
        indexer = Indexer(self.access_token, self.start_time, self.end_time)
        try:
            # Logic to read data from ms_teams_channel_chat_doc_ids.json file.
            if (os.path.exists(constant.CALENDAR_CHAT_DEINDEXING_PATH) and os.path.getsize(constant.CALENDAR_CHAT_DEINDEXING_PATH) > 0):
                with open(constant.CALENDAR_CHAT_DEINDEXING_PATH, encoding="UTF-8") as ids_store:
                    try:
                        ids_collection = json.load(ids_store)
                        ids_collection["global_keys"] = ids_collection.get("global_keys") or []
                        doc_ids_storage = ids_collection.get("global_keys") or []
                    except ValueError as exception:
                        logger.exception(
                            "Error while parsing the json file of the ids store from path: %s. Error: %s"
                            % (constant.CALENDAR_CHAT_DEINDEXING_PATH, exception)
                        )
            storage_with_collection["delete_keys"] = copy.deepcopy(
                ids_collection.get("global_keys"))
            # Logic to get user chat, meeting chat, attachments, tabs and meeting recoding from Microsoft Team based on our last checkpoint.
            user_msg = cal.MSTeamsCalendar(self.access_token, self.start_time, self.end_time, indexer.get_schema_fields, logger)
            calendar_permisssions, documents, is_error = user_msg.get_calendars(doc_ids_storage)
            if self.permission:
                for member, id in calendar_permisssions.items():
                    indexer.index_permissions(member, id)
            indexer.bulk_index_document(documents, constant.CALENDAR)
            storage_with_collection["global_keys"] = list(doc_ids_storage)
            with open(constant.CALENDAR_CHAT_DEINDEXING_PATH, "w", encoding="UTF-8") as f:
                try:
                    json.dump(storage_with_collection, f, indent=4)
                except ValueError as exception:
                    logger.warn('Error while adding ids to json file. Error: %s' % (exception))
        except Exception as exception:
            print_and_log(
                self.logger,
                "exception",
                "[Fail] Error while indexing the calendars. Error: %s" % (exception),
            )
        is_error_shared.append(self.is_error)
        logger.info("Completed indexing calendars to the Workplace Search")


def datetime_partitioning(start_time, end_time, processes):
    """ Divides the timerange in equal partitions by number of processors
        :param start_time: Start time of the interval
        :param end_time: End time of the interval
        :param processes: Number of processors the device have
    """
    start_time = datetime.strptime(start_time, constant.DATETIME_FORMAT)
    end_time = datetime.strptime(end_time, constant.DATETIME_FORMAT)

    diff = (end_time - start_time) / processes
    for idx in range(processes):
        yield (start_time + diff * idx)
    yield end_time


def init_multiprocessing(access_token, start_time, end_time, type_, is_error_shared, user_drive):
    """This method initializes the FetchIndex class and kicks-off the multiprocessing. This is a wrapper method added to fix the pickling issue while using multiprocessing in Windows
            :param access_token: ms teams access token
            :param start_time: start time of the indexing
            :param end_time: end time of the indexing
            :param type_: object name
            :param is_error_shared: list of all the is_error values
            :param user_drive: dictonary of dictonary

        """
    logger.info(
        "Successfully fetched the checkpoint details: start_time: %s and end_time: %s, calling the indexing"
        % (start_time, end_time)
    )
    indexer = Indexer(access_token, start_time, end_time)
    if type_ == 'calendar':
        indexer.index_calendar(is_error_shared)


def start_multiprocessing(indexing_type, config, access_token, calendar_token=""):
    """ This method manages the multiprocessing in the ms teams objects
        :param indexing_type: Type of indexing (full sync or incremental)
        :param config: Configuration values
        :param access_token: MS Teams access token
    """
    worker_process = config.get("worker_process")
    is_error_shared_chats = multiprocessing.Manager().list()
    is_error_shared_teams = multiprocessing.Manager().list()
    is_error_shared_calander = multiprocessing.Manager().list()
    user_drive = multiprocessing.Manager().dict()
    jobs = []
    obj_permissions_list = ["teams", "channels", "channel_messages", "channel_tabs", "channel_documents"]
    check = Checkpoint(logger)
    if any(obj in config.get('objects') for obj in obj_permissions_list) and "user_chats" in config.get('objects') and worker_process != 1:
        worker_process = round((worker_process) / 2)

    if any(obj in config.get('objects') for obj in obj_permissions_list):
        end_time_teams, datelist = get_partition_time(indexing_type, config, worker_process, check, "teams")
        define_processes(access_token, worker_process, is_error_shared_teams, jobs, datelist, user_drive, job_type="teams")

    if "user_chats" in config.get('objects'):
        end_time_chats, datelist = get_partition_time(indexing_type, config, worker_process, check, "user_chats")
        define_processes(access_token, worker_process, is_error_shared_chats, jobs, datelist, user_drive, job_type="user_chats")

    if "calendar" in config.get('objects'):
        if indexing_type == "incremental":
            start_time_cal, end_time_cal = check.get_checkpoint(
                constant.CURRENT_TIME, "calendar")
        else:
            start_time_cal = config.get("start_time")
            end_time_cal = constant.CURRENT_TIME
        process = multiprocessing.Process(target=init_multiprocessing, args=(calendar_token, start_time_cal, end_time_cal, "calendar", is_error_shared_calander, user_drive))
        jobs.append(process)

    for job in jobs:
        job.start()
    for job in jobs:
        job.join()

    logger.info("Saving the checkpoints")
    if is_error_shared_teams and True not in is_error_shared_teams:
        check.set_checkpoint(end_time_teams, indexing_type, "teams")
    if is_error_shared_chats and True not in is_error_shared_chats:
        check.set_checkpoint(end_time_chats, indexing_type, "user_chats")
    if is_error_shared_calander and True not in is_error_shared_calander:
        check.set_checkpoint(end_time_cal, indexing_type, "calendar")


def define_processes(token, worker_process, is_error_shared, jobs, datelist, user_drive, job_type):
    """ Creates a list of jobs for multiprocessing
        :param token: ms teams access token
        :param worker_process: number of processes in multiprocessing
        :param is_error_shared: list of all the is_error values for a given object type
        :param jobs: list of processes for multiprocessing
        :param datelist: time range partitions for each process
        :param user_drive: dictonary of dictonary
        :param job_type: type of ms teams object (teams or user-chats)
    """
    for num in range(0, worker_process):
        start_time_partition = datelist[num]
        end_time_partition = datelist[num + 1]
        process = multiprocessing.Process(target=init_multiprocessing, args=(token, start_time_partition, end_time_partition, job_type, is_error_shared, user_drive))
        jobs.append(process)


def get_partition_time(indexing_type, config, worker_process, check, type_):
    """ Divides the time range of indexing into partitions based on number of processes.
       :param indexing_type: The type of the indexing i.e. Incremental Sync or Full sync
       :param config: Configuration values
       :param worker_process: Number of processes in multiprocessing
       :param check: Checkpoint class object
       :param type_: Object type (teams or user_chats)
    """
    if indexing_type == "incremental":
        start_time, end_time = check.get_checkpoint(
            constant.CURRENT_TIME, type_)
    else:
        start_time = config.get("start_time")
        end_time = constant.CURRENT_TIME

    partitions = list(datetime_partitioning(start_time, end_time, worker_process))
    datelist = []
    for sub in partitions:
        datelist.append(sub.strftime(constant.DATETIME_FORMAT))
    return end_time, datelist


def start(indexing_type):
    """ Runs the indexing logic regularly after a given interval
        or puts the connector to sleep
        :param indexing_type: The type of the indexing i.e. Incremental Sync or Full sync
    """
    logger.info("Starting the indexing...")
    config = Configuration(logger).configurations
    calendar_token = ""
    if config.get("enable_document_permission"):
        UserGroupPermissions(logger).remove_all_permissions()
    docids_dir = os.path.dirname(constant.USER_CHAT_DEINDEXING_PATH)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(docids_dir):
        os.makedirs(docids_dir)

    while True:
        token = MSALAccessToken(logger)
        if indexing_type == "incremental":
            interval = config.get("indexing_interval")
        else:
            interval = config.get("full_sync_interval")
        if "calendar" in config.get("objects"):
            calendar_token = token.get_token(is_aquire_for_client=True)
        token = token.get_token()
        start_multiprocessing(indexing_type, config, token, calendar_token=calendar_token)
        # TODO: need to use schedule instead of time.sleep
        logger.info("Sleeping..")
        time.sleep(interval * 60)


if __name__ == "__main__":
    start("incremental")
