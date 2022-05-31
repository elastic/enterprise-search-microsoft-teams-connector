#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
""" This module fetches all calendars events from Microsoft Teams.
"""
import calendar as cal
from datetime import datetime

from . import constant
from .microsoft_teams_client import MSTeamsClient
from .microsoft_teams_users import MSTeamsUsers
from .utils import check_response, insert_document_into_doc_id_storage

USER_MEETING_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
MEETING = "Meeting"


class MSTeamsCalendar:
    """Fetches calendars for all users from Microsoft Teams"""

    def __init__(self, access_token, get_schema_fields, logger, config):
        self.token = access_token
        self.get_schema_fields = get_schema_fields
        self.client = MSTeamsClient(logger, self.token, config)
        self.users = MSTeamsUsers(self.token, logger)
        self.logger = logger
        self.config = config
        self.objects = config.get_value('objects')

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
                day_pattern = f"on day {pattern['dayOfMonth']}" if pattern[
                    'dayOfMonth'] else f"on {pattern['index']} {','.join(pattern['daysOfWeek'])}"
                days = f"year {day_pattern} of {cal.month_name[pattern['month']]}"
            # If type of meeting  is monthly so body will be: Recurrence: Occurs every month on day 5 of march
            # starting {date} until {enddate}
            elif pattern['type'] in ['absoluteMonthly', 'relativeMonthly']:
                days_pattern = f"on day {pattern['dayOfMonth']}" if pattern[
                    'dayOfMonth'] else f"on {pattern['index']} {','.join(pattern['daysOfWeek'])}"
                days = f"{occurrence} month {days_pattern}"
            # Else goes in weekly situation where body will be: Recurrence: Occurs Every 3 week on monday,tuesday,
            # wednesday starting {date} until {enddate}
            else:
                week = ','.join(pattern['daysOfWeek'])
                days = f"{occurrence} week on {week}"
            date = f"{range['startDate']}" if range['type'] == 'noEnd' else f"{range['startDate']} "\
                f"until {range['endDate']}"
            recurrance = f"Occurs Every {days} starting {date}"
            body = f'Recurrence: {recurrance} \nOrganizer: {calendar["organizer"]["emailAddress"]["name"]} '\
                f'\nAttendees: {attendees} \nDescription: {calendar["bodyPreview"]}'
        else:
            start_time = datetime.strptime(calendar["start"]["dateTime"][: -4], USER_MEETING_DATETIME_FORMAT).strftime(
                "%d %b, %Y at %H:%M")
            end_time = datetime.strptime(calendar["end"]["dateTime"][: -4], USER_MEETING_DATETIME_FORMAT).strftime(
                "%d %b, %Y at %H:%M")
            body = f'Schedule: {start_time} to {end_time} \nOrganizer: '\
                f'{calendar["organizer"]["emailAddress"]["name"]} \nAttendees: {attendees} '\
                f'\nDescription: {calendar["bodyPreview"]}'
        return body

    def get_calendars(self, ids_list, start_time, end_time):
        """ Fetches all calendar events from Microsoft Teams.
            :param ids_list: List of ids
            Returns:
                permissions_dict: List of dictionaries containing calendar id and their members
                documents: Documents to be indexed in Workplace Search
        """
        self.logger.debug("Fetching users for Calendar")
        users = self.users.get_all_users()
        cal_schema = self.get_schema_fields("calendar", self.objects)
        documents = []
        permissions_dict = {}
        self.logger.info("Fetched the users metadata. Attempting to extract the meetings from the calendar..")
        for val in users:
            # Logic to append calendar for deletion
            insert_document_into_doc_id_storage(ids_list, val["userId"], constant.USER, "", "")
            try:
                calendar_response = self.client.get(
                    f'{constant.GRAPH_BASE_URL}/users/{val["userId"]}/events', constant.CALENDAR, True, True,
                    page_size=50, filter_query=f"lastModifiedDateTime ge {start_time} and lastModifiedDateTime "
                    f"le {end_time}")
                calendar_detail_response = check_response(
                    self.logger, calendar_response, "Could not fetch calendar events",
                    "[Fail] Error while fetching calendar details from teams.")
                if calendar_detail_response:
                    for calendar in calendar_detail_response:
                        if not calendar['isCancelled']:
                            # Logic to append calendar for deletion
                            insert_document_into_doc_id_storage(ids_list, calendar["id"], constant.CALENDAR,
                                                                val["userId"], "")
                            calendar_dict = {"url": "", "type": MEETING}
                            attendee_list = []
                            permissions_dict[val["displayName"]] = [*permissions_dict.get(val["displayName"], []) + [
                                calendar["id"]]]
                            for att in calendar['attendees']:
                                attendee_list.append(f"{att['emailAddress']['name']}"
                                                     f"({att['emailAddress']['address']})")
                            attendees = ",".join(attendee_list)
                            body = self.get_calendar_detail(attendees, calendar)
                            for ws_field, ms_fields in cal_schema.items():
                                calendar_dict[ws_field] = calendar[ms_fields]
                            calendar_dict['body'] = body
                            if calendar['onlineMeeting']:
                                calendar_dict['url'] = calendar["onlineMeeting"]['joinUrl']
                            if self.config.get_value("enable_document_permission"):
                                calendar_dict["_allow_permissions"] = [calendar['id']]
                            documents.append(calendar_dict)
            except Exception as exception:
                self.logger.exception(f"Error while fetching the calendar events from teams. Error: {exception}")
                raise exception
        return permissions_dict, documents
