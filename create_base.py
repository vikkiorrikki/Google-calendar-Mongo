# -*- coding: utf-8 -*-
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from pymongo import MongoClient

import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'C:/Users/Admin/Desktop/calendar/client_secret.json'
APPLICATION_NAME = 'Google Calendar + MongoDB'


def get_credentials():

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # совместимость с python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_param(entry, param1, param2=None):
    if param2 is None:
        try:
            result = entry[param1]
        except KeyError:
            result = 'non specified'
        return result
    else:
        try:
            result = entry[param1].get(param2)
        except KeyError:
            result = 'non specified'
        return result

def main():

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # utc - формат
    year = (datetime.datetime.utcnow() + datetime.timedelta(days=365)).isoformat() + 'Z'

    client = MongoClient('localhost', 27017)
    db = client['calendar-data']
    mongo_calendars = db.calendars
    empty = mongo_calendars.count() == 0
    print ('Base is empty:', empty)
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            cal_id = get_param(calendar_list_entry, 'id')
            cal_summary = get_param(calendar_list_entry, 'summary')
            cal_descr = get_param(calendar_list_entry, 'description')
            mongo_calendars.update_one({'_id':cal_id}, {"$set":{'summary':cal_summary, 'description':cal_descr}}, upsert=True)

            events = service.events().list(calendarId=cal_id, timeMin=now, timeMax=year, singleEvents=True).execute()
            print('calendar ', cal_summary)
            for event in events['items']:

                start_time = get_param(event, 'start', 'dateTime')
                if start_time is None:
                    start_time = get_param(event, 'start', 'date') + 'T00:00:00+03:00';
                    end_time = get_param(event, 'end', 'date') + 'T00:00:00+03:00';
                else:
                    end_time = get_param(event, 'end', 'dateTime')
                event_id = get_param(event, 'id')
                event_sum = get_param(event, 'summary')
                event_descr = get_param(event, 'description')
                creator = get_param(event, 'creator', 'email')
                
                event_found = mongo_calendars.find_one({'_id':cal_id, 'events._id':event_id})
                if event_found is None:
                    mongo_calendars.update_one({'_id':cal_id}, 
                    {"$push":{'events':{'_id':event_id, 'start':start_time, 'end':end_time, 'title':event_sum, 'creator':creator, 'info':event_descr}}},
                    upsert=True)
                    print (cal_id, event_sum)
                else:
                    print ('skipping already existing event', event_id)

                attendees = get_param(event,'attendees')
                if attendees != 'non specified':
                    for attendee in attendees:
                        mongo_calendars.update_one({'_id':cal_id, 'events._id':event_id}, 
                        {"$push":{'events.$.attendees':get_param(attendee, 'email')}},
                        upsert=False)
                mongo_calendars.update_one({'_id':cal_id}, {"$pull":{'events':{'_id':0}}},upsert=True)

            print('end')
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            print('done!')
            break

if __name__ == '__main__':
    main()