import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials
execfile("params.conf", config)

json_key = json.load(open(google_oauth2_file))
scope = ['https://spreadsheets.google.com/feeds']
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
		sh = gc.open_by_key(amion_spreadsheet_id)
		ws = sh.worksheet(amion_worksheet_schedule, head=4) # let the fourth line be the header
		records = ws.get_all_records()
		return records

	def lookup_phone_by_extension(ext):		
		#get matching extension (O(N) time lookup...)
		for record in self.personnel:
			if ext == record['Extension']:
				return '+1' + sanitize.sub('', record['Telephone']) # if we found the extension
		return None # if no return

	def lookup_phone_by_name(name):
		#get matching extension (O(N) time lookup...)
		for record in self.personnel:
			if name == record['Name']:
				return '+1' + sanitize.sub('', record['Telephone']) # if we found the extension
		return None # if no return

	def lookup_name_in_schedule(person_type, lookup_date):
		# get relevant keys
		keys = [i for i in self.schedule.keys() if person_type.lower() in i.lower()]
		# get matching line in schedule (O(N) time lookup...)
		for record in self.schedule:
			if record['Date'] == lookup_date:
				return [record[i] for i in keys]
		return [] # return empty list
	
