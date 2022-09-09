#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
""" This module fetches all calendars events from Microsoft Teams.
"""
from calendar import month_name
from collections import defaultdict
from datetime import datetime

from . import constant
from .microsoft_teams_client import MSTeamsClient
from .microsoft_teams_users import MSTeamsUsers
from .utils import get_schema_fields

USER_MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
MEETING = "Meeting"


class MSTeamsCalendar:
    """Fetches calendars for all users from Microsoft Teams"""

    def __init__(self, access_token, logger, config, local_storage):
        self.token = access_token
        self.local_storage = local_storage
        self.client = MSTeamsClient(logger, self.token, config)
        self.users_obj = MSTeamsUsers(self.token, logger)
        self.logger = logger
        self.config = config
        self.object_type_to_index = config.get_value('object_type_to_index')

    def get_calendar_detail(self, attendees, calendar):
        """This method is used to fetch the calendar details for creating body in the workplace
           :param attendees: All the attendees seprated by comma
           :param calendar: Dictionary of event details
           Returns: body: body with event details which going to be indexed in Workplace Search
        """
        body = ''
        if calendar['recurrence']:
            range = calendar['recurrence']['range']
            pattern = calendar['recurrence']['pattern']
            occurrence = f"{pattern['interval']}" if pattern['interval'] else ""

            # In case type of meeting is daily so body will be: Recurrence: Occurs every 1 day starting {startdate}
            # until {enddate}
            if pattern['type'] == 'daily':
                days = f"{occurrence} day"

            # If type of meeting  is yearly so body will be: Recurrence: Occurs every year on day 5 of march starting
            # {date} until {enddate}
            elif pattern['type'] in ['absoluteYearly', 'relativeYearly']:
                day_pattern = f"on day {pattern['dayOfMonth']}" if pattern['dayOfMonth'] else "on "  \
                              f"{pattern['index']} {','.join(pattern['daysOfWeek'])}"
                days = f"year {day_pattern} of {month_name[pattern['month']]}"

            # If type of meeting  is monthly so body will be: Recurrence: Occurs every month on day 5 of march
            # starting {date} until {enddate}
            elif pattern['type'] in ['absoluteMonthly', 'relativeMonthly']:
                days_pattern = f"on day {pattern['dayOfMonth']}" if pattern['dayOfMonth'] else f"on "  \
                               f"{pattern['index']} {','.join(pattern['daysOfWeek'])}"
                days = f"{occurrence} month {days_pattern}"

            # Else goes in weekly situation where body will be: Recurrence: Occurs Every 3 week on monday,tuesday,
            # wednesday starting {date} until {enddate}
            else:
                week = ','.join(pattern['daysOfWeek'])
                days = f"{occurrence} week on {week}"

            date = f"{range['startDate']}" if range['type'] == 'noEnd' else f"{range['startDate']} until "  \
                   f"{range['endDate']}"
            recurrance = f"Occurs Every {days} starting {date}"
            body = f'Recurrence: {recurrance} \nOrganizer: {calendar["organizer"]["emailAddress"]["name"]} '  \
                   f'\nAttendees: {attendees} \nDescription: {calendar["bodyPreview"]}'

        else:
            start_time = datetime.strptime(calendar["start"]["dateTime"][: -4], USER_MEETING_DATETIME_FORMAT).strftime(
                "%d %b, %Y at %H:%M")
            end_time = datetime.strptime(calendar["end"]["dateTime"][: -4], USER_MEETING_DATETIME_FORMAT).strftime(
                "%d %b, %Y at %H:%M")
            body = f'Schedule: {start_time} to {end_time} \nOrganizer: '  \
                   f'{calendar["organizer"]["emailAddress"]["name"]} \nAttendees: {attendees} \nDescription: '  \
                   f'{calendar["bodyPreview"]}'
        return body

    def get_calendars(self, ids_list, start_time, end_time):
        """ Fetches all calendar events from Microsoft Teams.
            :param ids_list: List of ids
            Returns:
                permissions_dict: List of dictionaries containing calendar id and their members
                documents: Documents to be indexed in Workplace Search
        """
        self.logger.debug("Fetching users for Calendar Events")
        users = self.users_obj.get_all_users()
        self.logger.info("Fetched the users metadata. Attempting to extract the meetings from the calendar...")

        documents = []
        permissions_dict = defaultdict(list)
        calendar_schema = get_schema_fields("calendar", self.object_type_to_index)

        for user in users:
            # Logic to append calendar for deletion
            self.local_storage.insert_document_into_doc_id_storage(ids_list, user["userId"], constant.USER, "", "")
            try:
                response = self.client.get_calendars(
                    next_url=f'{constant.GRAPH_BASE_URL}/users/{user["userId"]}/events',
                    start_time=start_time,
                    end_time=end_time
                )

                if not response:
                    continue

                for calendar in response:
                    if not calendar['isCancelled']:
                        # Logic to append calendar for deletion
                        self.local_storage.insert_document_into_doc_id_storage(
                            ids_list,
                            calendar["id"],
                            constant.CALENDAR,
                            user["userId"],
                            ""
                        )

                        calendar_dict = {"type": MEETING}
                        permissions_dict[user["displayName"]].append(calendar["id"])

                        attendee_list = []
                        for att in calendar['attendees']:
                            attendee_list.append(f"{att['emailAddress']['name']}"
                                                 f"({att['emailAddress']['address']})")

                        attendees = ",".join(attendee_list)
                        body = self.get_calendar_detail(attendees, calendar)

                        for ws_field, ms_fields in calendar_schema.items():
                            calendar_dict[ws_field] = calendar[ms_fields]
                        calendar_dict['body'] = body

                        if calendar['onlineMeeting']:
                            calendar_dict['url'] = calendar["onlineMeeting"]['joinUrl']

                        calendar_dict["_allow_permissions"] = []
                        if self.config.get_value("enable_document_permission"):
                            calendar_dict["_allow_permissions"] = [calendar['id']]
                        documents.append(calendar_dict)
            except Exception as exception:
                self.logger.exception(f"Error while fetching the calendar events from teams. Error: {exception}")
                raise exception
        return permissions_dict, documents
