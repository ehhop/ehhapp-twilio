#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.config import *

import json, re, os, pytz
import gspread
from oauth2client.client import SignedJwtAssertionCredentials
from datetime import datetime, timedelta, date, time

json_key = json.load(open(google_oauth2_file))
scope = ['https://spreadsheets.google.com/feeds']

# Google stuff
# Look up SignedJwtAssertionCredentials
credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)

class EHHOPdb:
	
	def __init__(self, credentials):
		self.conn = gspread.authorize(credentials)
		self.personnel = self.getdb()
		self.schedule = self.getschedule()
		self.sanitize = re.compile(r'[^\d]+')
	
	def __repr__(self):
		return "<class EHHOPdb>"
		
	def getdb(self):
		# download phone records
		sh = self.conn.open_by_key(amion_spreadsheet_id)
		ws = sh.worksheet(amion_worksheet_name)
		records = ws.get_all_records()
		#remove header lines or those deactivated by '#'
		records = [i for i in records if i['Name'][0] != "#"]
		return records

	def getschedule(self):
		# download schedule
		sh = self.conn.open_by_key(amion_spreadsheet_id)
		ws = sh.worksheet(amion_worksheet_schedule) 
		records = ws.get_all_records(head=4) #4th line is header
		return records

	def lookup_phone_by_extension(self, ext):		
		# get matching extension (O(N) time lookup...)
		# ext should already be an int
		for record in self.personnel:
			if ext == record['Extension']:
				return [record['Name'], '+1' + self.sanitize.sub('', record['Telephone']), record['Email']] # if we found the extension

	def lookup_phone_by_name(self, name):
		#get matching extension (O(N) time lookup...)
		for record in self.personnel:
			if name == record['Name']:
				return '+1' + self.sanitize.sub('', record['Telephone']) # if we found the extension
		return None # if no return

	def lookup_email_by_name(self, name):
		#get matching extension (O(N) time lookup...)
		for record in self.personnel:
			if name == record['Name']:
				return record['Email'] # if we found the extension
		return None # if no return

	def lookup_name_in_schedule(self, person_type, lookup_date):
		# get relevant keys
		if (person_type == '') | (person_type==None):
			return []
		keys = [i for i in self.schedule[0].keys() if person_type.lower() in i.lower()]
		# get matching line in schedule (O(N) time lookup...)
		for record in self.schedule:
			if record['Date'] == lookup_date:
				return [a for i in keys if record[i] != '' for a in record[i].split("\n")]
		return [] # return empty list
	
	def lookup_name_by_position(self, person_type):
		# get matching person
		people = []
		for record in self.personnel:
			if person_type.lower() in record['Position'].lower():
				people.append([record['Name'], '+1' + self.sanitize.sub('', record['Telephone']), record['Email']])
		return people # return empty list

def getOnCallPhoneNum():
	database = EHHOPdb(credentials)
        return_num = None
        try:
                return_names = database.lookup_name_in_schedule("On Call Medical Clinic TS", getSatDate())
                if return_names != []:
                        return_num = database.lookup_phone_by_name(return_names[0])
		return return_num
        except:
                return fallback_phone

def getSatDate():
        # get next saturday's date
        time_now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = time_now.weekday()
        addtime = None
        if day_of_week == 6:
                addtime=timedelta(6)
        else:
                addtime=timedelta(5-day_of_week)
        satdate = (time_now+addtime).strftime('%-m/%-d/%Y')
        return satdate
