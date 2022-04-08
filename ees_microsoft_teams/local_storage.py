import json


class LocalStorage:
    """This class contains all the methods to do operations on doc_id json file
    """

    def __init__(self, logger):
        self.logger = logger

    def load_storage(self, ids_path):
        """This method fetches the contents of doc_id.json(local ids storage)
            :param ids_path: Path to the respective doc_ids.json
        """

        try:
            with open(ids_path, encoding='utf-8') as ids_file:
                try:
                    return json.load(ids_file)
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while parsing the json file of the ids store from path: {ids_path}. Error: {exception}"
                    )
        except FileNotFoundError:
            self.logger.debug(f"Local storage for ids was not found with path: {ids_path}.")
            return {"global_keys": {}}

    def update_storage(self, ids, ids_path):
        """This method is used to update the ids stored in doc_id.json file
            :param ids: updated ids to be stored in the doc_id.json file
            :param ids_path: Path to the respective doc_ids.json
        """
        with open(ids_path, "w", encoding='utf-8') as ids_file:
            try:
                json.dump(ids, ids_file, indent=4)
            except ValueError as exception:
                self.logger.exception(
                    f"Error while updating the doc_id json file. Error: {exception}"
                )
