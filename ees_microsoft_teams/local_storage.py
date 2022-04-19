import copy
import json
import os

from . import constant


class LocalStorage:
    """This class contains all the methods to do operations on doc_id json file"""

    def __init__(self, logger):
        self.logger = logger

    def load_storage(self, ids_path):
        """This method fetches the contents of doc_id.json(local ids storage)
        :param ids_path: Path to the respective doc_ids.json
        """

        try:
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

    def update_storage(self, ids, ids_path):
        """This method is used to update the ids stored in doc_id.json file
        :param ids: updated ids to be stored in the doc_id.json file
        :param ids_path: Path to the respective doc_ids.json
        """
        with open(ids_path, "w", encoding="utf-8") as ids_file:
            try:
                json.dump(ids, ids_file, indent=4)
            except ValueError as exception:
                self.logger.exception(
                    f"Error while updating the doc_id json file. Error: {exception}"
                )

    def create_local_storage_directory(self):
        """Creates a doc_id directory if not present"""
        doc_ids_directory = os.path.dirname(constant.USER_CHAT_DELETION_PATH)
        if not os.path.exists(doc_ids_directory):
            os.makedirs(doc_ids_directory)

    def get_storage_with_collection(self, ids_path):
        """Returns a dictionary containing the locally stored IDs of files fetched from Microsoft Teams
        :param ids_path: Path to the respective doc_ids.json
        """
        storage_with_collection = {"global_keys": [], "delete_keys": []}
        ids_collection = self.load_storage(ids_path)
        storage_with_collection["delete_keys"] = copy.deepcopy(
            ids_collection.get("global_keys")
        )
        if not ids_collection["global_keys"]:
            ids_collection["global_keys"] = []
        storage_with_collection["global_keys"] = copy.deepcopy(
            ids_collection["global_keys"]
        )
        return storage_with_collection
