#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import copy
import json
import os

from . import constant


class LocalStorage:
    """This class contains all the methods to do operations on doc_id json file"""

    def __init__(self, logger):
        self.logger = logger
        self.ids_path_dict = {
            "teams": constant.CHANNEL_CHAT_DELETION_PATH,
            "user_chats": constant.USER_CHAT_DELETION_PATH,
            "calendar": constant.CALENDAR_CHAT_DELETION_PATH
        }

    def load_storage(self, object_type):
        """This method fetches the contents of doc_id.json(local ids storage)
        :param ids_path: Path to the respective doc_ids.json
        """

        try:
            ids_path = self.ids_path_dict.get(object_type)
            if os.path.exists(ids_path) and os.path.getsize(ids_path) > 0:
                with open(ids_path, encoding="utf-8") as ids_file:
                    try:
                        return json.load(ids_file)
                    except ValueError as exception:
                        self.logger.exception(
                            f"Error while parsing the json file of the ids store from path: {ids_path}. "
                            f"Error: {exception}"
                        )
        except FileNotFoundError:
            self.logger.debug(
                f"Local storage for ids was not found with path: {ids_path}."
            )
        return {"global_keys": []}

    def update_storage(self, ids, object_type):
        """This method is used to update the ids stored in doc_id.json file
        :param ids: updated ids to be stored in the doc_id.json file
        :param ids_path: Path to the respective doc_ids.json
        """
        ids_path = self.ids_path_dict.get(object_type)
        with open(ids_path, "w", encoding="utf-8") as ids_file:
            try:
                json.dump(ids, ids_file, indent=4)
            except ValueError as exception:
                self.logger.exception(
                    f"Error while updating the doc_id json file. Error: {exception}"
                )
                raise exception

    def create_local_storage_directory(self):
        """Creates a doc_id directory if not present"""
        if not os.path.exists(constant.LOCAL_STORAGE_DIRECTORY):
            os.makedirs(constant.LOCAL_STORAGE_DIRECTORY)

    def get_documents_from_doc_id_storage(self, object_type):
        """Returns a dictionary from doc_id file containing the document ids fetched from Microsoft Teams
        :param ids_path: Path to the respective doc_ids.json
        Returns:
            document_ids_dictionary: Dictionary containing the Microsoft Teams document ids
        """
        document_ids_dictionary = {"global_keys": [], "delete_keys": []}
        ids_collection = self.load_storage(object_type)
        document_ids_dictionary["delete_keys"] = copy.deepcopy(
            ids_collection.get("global_keys")
        )
        if not ids_collection["global_keys"]:
            ids_collection["global_keys"] = []

        document_ids_dictionary["global_keys"] = copy.deepcopy(
            ids_collection["global_keys"]
        )
        return document_ids_dictionary

    def insert_document_into_doc_id_storage(self, ids_list, id, type, parent_id="", super_parent_id=""):
        """ Prepares the document dictionary for deletion and insert it into the global_keys of respective doc_ids.json.
            :param ids_list: Pass "global_keys" of microsoft_teams_user_chat_doc_ids.json,
                microsoft_teams_channel_chat_doc_ids.json and microsoft_teams_calendar_doc_ids.json
            :param id: Pass id of User Chat, User Chat Attachment, Calendar, Calendar Attachment, Teams, Channel Chat,
                Channel Chat Attachment, Channel Chat Tabs and User Chat Tabs
            :param type: Pass type of each document for deletion.
            :param parent_id: Pass parent id of each document for deletion.
            :param super_parent_id: Pass super parent id of each document for deletion
        """
        new_item = {"id": str(id), "type": type, "parent_id": str(parent_id), "super_parent_id": str(super_parent_id)}
        if new_item not in ids_list:
            ids_list.append(new_item)
        return ids_list
