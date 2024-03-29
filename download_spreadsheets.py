#!/usr/bin/env python
import sys, os
import site
site.addsitedir('/var/wsgiapps/ehhapp_twilio/venv/lib/python2.7/site-packages')

PROJECT_DIR = '/var/wsgiapps/ehhapp_twilio/'
sys.path.append(PROJECT_DIR)
sys.path.append(PROJECT_DIR + '/venv')

activate_this = os.path.expanduser('/var/wsgiapps/ehhapp_twilio/venv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from ehhapp_twilio.config import *
from ehhapp_twilio.python_gmail_oauth2_v2 import *
import gspread, json
#json_key = json.load(open(google_oauth2_file))
scope = ['https://spreadsheets.google.com/feeds']
credentials = get_credentials()

not_downloaded=True
count = 0
while not_downloaded & (count<10):
    try:
        # set up
        conn = gspread.authorize(credentials)
        doc = conn.open_by_key(amion_spreadsheet_id)

        # get list of names
        spread1 = doc.worksheet(amion_worksheet_name)
        names = json.dumps(spread1.get_all_records())
        name_file = open(names_filename,'w')
        name_file.write(names)
        name_file.close()

        # get schedule
        spread2 = doc.worksheet(amion_worksheet_schedule)
        sched = json.dumps(spread2.get_all_records(head=4))
        sched_file = open(schedule_filename,'w')
        sched_file.write(sched)
        sched_file.close()
        not_downloaded=False
    except gspread.exceptions.APIError as msg:
        count += 1
        if count >= 10:
            print("Automatic retry failed.")
            raise Exception(msg)
        continue
