# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import os
import json
from src import constant
from src.base_class import BaseClass
from src.schema import validate_date_new
from src.utils import print_and_log


class Checkpoint(BaseClass):
    def __init__(self, logger):
        BaseClass.__init__(self, logger=logger)
        self.logger = logger

    def get_checkpoint(self, current_time, obj_type):
        """ This method fetches the checkpoint from the checkpoint file in
            the local storage. If the file does not exist, it takes the
            checkpoint details from the configuration file.
            :param current_time: Current time
            :param obj_type: Object type to fetch the checkpoint
        """
        self.logger.info(
            f"Fetching the checkpoint details for {obj_type} from the checkpoint file: %s"
            % constant.CHECKPOINT_PATH
        )

        start_time = self.configurations.get("start_time")
        end_time = self.configurations.get("end_time")

        if (os.path.exists(constant.CHECKPOINT_PATH) and os.path.getsize(constant.CHECKPOINT_PATH) > 0):
            self.logger.info(
                "Checkpoint file exists and has contents, hence considering the checkpoint time instead of start_time and end_time"
            )
            with open(constant.CHECKPOINT_PATH, encoding="UTF-8") as checkpoint_store:
                try:
                    checkpoint_list = json.load(checkpoint_store)

                    if not checkpoint_list.get(obj_type):
                        self.logger.info(
                            f"The checkpoint file is present but it does not contain the start_time for {obj_type}, hence considering the start_time and end_time from the configuration file instead of the last successful fetch time"
                        )
                    else:
                        try:
                            start_time = validate_date_new(checkpoint_list.get(obj_type)).strftime(constant.DATETIME_FORMAT)
                            end_time = current_time
                        except ValueError:
                            print_and_log(self.logger, "exception", f"Start time: {checkpoint_list.get(obj_type)} for {obj_type} in the checkpoint file {constant.CHECKPOINT_PATH} is not in the correct format. Expected format: {constant.DATETIME_FORMAT}. Remove the checkpoint entry for the {obj_type} or fix the format of the checkpoint to continue indexing")
                            exit(0)
                except ValueError as exception:
                    self.logger.exception(
                        f"Error while parsing the json file of the checkpoint store from path: {constant.CHECKPOINT_PATH}. Error: {exception}"
                    )
                    self.logger.info(
                        "Considering the start_time and end_time from the configuration file"
                    )

        else:
            self.logger.info(
                f"Checkpoint file does not exist at {constant.CHECKPOINT_PATH}, considering the start_time and end_time from the configuration file"
            )

        self.logger.info(
            f"Contents of the start_time: {start_time} and end_time: {end_time} for {obj_type}",
        )
        return start_time, end_time

    def set_checkpoint(self, current_time, index_type, obj_type):
        """ This method updates the existing checkpoint json file or creates
            a new checkpoint json file in case it is not present
            :param current_time: Current time
            :index_type: Indexing type from "incremental" or "full_sync"
            :param obj_type: Object type to set the checkpoint
        """
        try:
            with open(constant.CHECKPOINT_PATH, encoding="UTF-8") as checkpoint_store:
                checkpoint_list = json.load(checkpoint_store)
                if checkpoint_list.get(obj_type):
                    self.logger.info(
                        f"Setting the checkpoint contents: {current_time} for the {obj_type} to the checkpoint path: {constant.CHECKPOINT_PATH}"
                    )
                    checkpoint_list[obj_type] = current_time
                else:
                    self.logger.info(
                        f"Setting the checkpoint contents: {self.configurations.get('end_time')} for the {obj_type} to the checkpoint path: {constant.CHECKPOINT_PATH}"
                    )
                    checkpoint_list[obj_type] = self.configurations.get('end_time')
        except Exception as exception:
            if isinstance(exception, FileNotFoundError):
                self.logger.info(
                    f"Checkpoint file not found on path: {constant.CHECKPOINT_PATH}. Generating the checkpoint file"
                )
            else:
                self.logger.exception(
                    f"Error while fetching the json file of the checkpoint store from path: {constant.CHECKPOINT_PATH}. Error: {exception}"
                )
            if index_type == "incremental":
                checkpoint_time = self.configurations.get('end_time')
            else:
                checkpoint_time = current_time
            self.logger.info(
                f"Setting the checkpoint contents: {checkpoint_time} for the {obj_type} to the checkpoint path: {constant.CHECKPOINT_PATH}"
            )
            checkpoint_list = {obj_type: checkpoint_time}

        with open(constant.CHECKPOINT_PATH, "w", encoding="UTF-8") as checkpoint_store:
            try:
                json.dump(checkpoint_list, checkpoint_store, indent=4)
                self.logger.info("Successfully saved the checkpoint")
            except ValueError as exception:
                self.logger.exception(
                    f"Error while updating the existing checkpoint json file. Adding the new content directly instead of updating. Error: {exception}"
                )
