#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.config import *

import json, re, os, pytz
from datetime import datetime, timedelta, date, time

credentials = {"names": names_filename, "schedule": schedule_filename}

class EHHOPdb:							# our Google Drive database
	
	def __init__(self, credentials):			# get all the data, assemble it into python variables
		self.conn = credentials
		self.personnel = self.getdb()
		self.schedule = self.getschedule()
		self.sanitize = re.compile(r'[^\d]+')		# for fixing wanky phone numbers into just digits to dial
	
	def __repr__(self):
		return "<class EHHOPdb>"
		
	def getdb(self):
		# download phone records
		filen = self.conn["names"]
		records = json.load(open(filen))
		#remove header lines or those deactivated by '#'
		records = [i for i in records if i['Name'][0] != "#"]
		return records

	def getschedule(self):
		# download schedule
		filen = self.conn["schedule"]
		records = json.load(open(filen))
		return records

	def lookup_phone_by_extension(self, ext):		
		# get matching extension (O(N) time lookup...)
		# ext should already be an int
		for record in self.personnel:
			if ext == record['Extension']:
				return [record['Name'], '+1' + self.sanitize.sub('', record['Telephone']), record['Email']] # if we found the extension

	def lookup_phone_by_name(self, name):
		# get a phone number from a name, like from the schedule
		for record in self.personnel:
			if name.strip() == record['Name'].strip():
				return '+1' + self.sanitize.sub('', record['Telephone']) # if we found the extension
		return None # if no return

	def lookup_email_by_name(self, name):
		# get an email from a name, like from the schedule
		for record in self.personnel:
			if name.strip() == record['Name'].strip():
				return record['Email'] # if we found the extension
		return None # if no return

	def lookup_name_in_schedule(self, person_type, lookup_date):
		# get a name based on the position title in the schedule
		if (person_type == '') | (person_type==None):
			return []
		keys = [i for i in self.schedule[0].keys() if person_type.lower() in i.lower()]
		# get matching line in schedule (O(N) time lookup...)
		for record in self.schedule:
			if record['Date'] == lookup_date:
				return [a for i in keys if record[i] != '' for a in record[i].split("\n")]
		return [] # return empty list
	
	def lookup_name_by_position(self, person_type):
		# get matching person in EHHOP personnel
		people = []
		for record in self.personnel:
			if person_type.lower() in record['Position'].lower():
				people.append([record['Name'].strip(), '+1' + self.sanitize.sub('', record['Telephone']), record['Email']])
		return people # return empty list

def getOnCallPhoneNum():					# get the on call phone #
	database = EHHOPdb(credentials)
        return_num = None
        try:
                return_names = database.lookup_name_in_schedule("On Call Medical Clinic TS", getlastSatDate())	# maybe we could add this to routes?
                if return_names != []:
                        return_num = database.lookup_phone_by_name(return_names[0])
		return return_num
        except:
                return fallback_phone				# fallback if fail to find the number

def getSatDate():
        # get next saturday's date for lookups in the schedule
        time_now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = time_now.weekday()
        addtime = None
        if day_of_week == 6:
                addtime=timedelta(6)
        else:
                addtime=timedelta(5-day_of_week)
        satdate = (time_now+addtime).strftime('%-m/%-d/%Y')
        return satdate

def getlastSatDate(): # go Wed-Wed
        # get next saturday's date for lookups in the schedule
        time_now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = time_now.weekday()
        addtime = None
        if day_of_week == 6:
        	addtime = timedelta(-1)
        elif day_of_week >= 2:
            addtime=timedelta(5-day_of_week)
        elif day_of_week < 2:
        	addtime = timedelta(-(2+day_of_week))
        satdate = (time_now+addtime).strftime('%-m/%-d/%Y')
        return satdate
