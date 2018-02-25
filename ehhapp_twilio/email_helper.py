#!/usr/bin/python
import sys
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.config import *
from ehhapp_twilio.database import db_session
from ehhapp_twilio.models import Intent, Assignment
from ehhapp_twilio.voicemail_helpers import add_voicemail
from ehhapp_twilio.webhooks import *

import smtplib, pytz, requests, random, string, re
from ftplib import FTP_TLS
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from requests.auth import HTTPBasicAuth
from twilio.rest import TwilioRestClient

from flask.ext.mail import Message

# Everything we do when we get a new VM

# user/pass to log into Twilio to retrieve files
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

def process_recording(recording_url, intent, ani, requireds=None, assign=None, no_requireds=False, caller_id=None, auth_method=auth_combo):
	'''process_recording(recording_url, intent, ani, requireds=None, assign=None, auth_method=auth_combo)
	recording_url:	URL of recording to download
	intent:		the digit pressed by the caller
	ani: 		caller ID
	requireds:	(optional) override the default required recipients
	assign:		(optional) override the default assigned recipients
	no_requireds:	(optional) do not send emails to requireds even if passed
	auth_method:	(optional) specify different twilio REST API credentials
	'''

	satdate = getlastSatDate() # get next clinic date
	recording_name = save_file(recording_url, auth_method) # save the file
	playback_url = player_url + recordings_base + recording_name
	slack_notify('<' + playback_url + '|New voicemail received>')
	db = EHHOPdb(credentials)

	# figure out who to send the message to
	if assign==None:
		db_assign = Assignment.query.filter_by(from_phone=ani[-10:], intent=intent).all()
		if db_assign != []: #someone is responsible for that phone number
			assign = [a.recipients.replace(" ", "").split(',') for a in db_assign]
			assign = [item for sublist in assign for item in sublist] # flatten array of arrays
			assign = ','.join(assign)
		else: # no one has the default assignment for that phone number
			intents = Intent.query.filter_by(digit=intent).first()
			sys.stderr.write(str(intents))
			assigns = intents.distributed_recipients.split(',')
			sys.stderr.write(str(assigns))
			assignlist = []
			for a in assigns:
				sys.stderr.write(str(a) + str(satdate))
				interresult = db.lookup_name_in_schedule(a, satdate)
				sys.stderr.write(str(interresult))
				emails = []
				for i in interresult:
					email = db.lookup_email_by_name(i)
					sys.stderr.write(str(email))
					emails.append(email) if email != None else None
				assignlist.append(emails)
			sys.stderr.write(str(assignlist))
			assign = []
			for c in assignlist:			
				c1 = [Assignment.query.filter_by(recipients=b).count() for b in c]
				assign_person = c[c1.index(min(c1))] if c != [] else ""
					# gets whoever has the lowest load (alphabetical tiebreak)
					# save the new assignment to the database for later retrieval
				if assign_person != "":
					assign.append(assign_person)
					new_assign = Assignment(from_phone=ani[-10:], recipients=assign_person, intent=intent)
					db_session.add(new_assign)
					db_session.commit()
			assign = ", ".join(assign)
	if requireds==None and not no_requireds:			# if no required recipients are sent and not a direct message
		db_requireds = Intent.query.filter_by(digit=intent).first()
		if db_requireds != None:
			requiredpos = db_requireds.required_recipients.split(',')
			requirelist = []
			for r in requiredpos:
				r = r.strip(" ")
				if "schedule:" in r.lower():
					a = r.split(":")[1].strip()
					interresult = db.lookup_name_in_schedule(a, satdate)
	                                sys.stderr.write(str(interresult))
                	                for i in interresult:
                        	                email = db.lookup_email_by_name(i)
                                	        sys.stderr.write(str(email))
                                        	requirelist.append(email) if email != None else None
				else:
					lookup = db.lookup_name_by_position(r)
					if lookup != []:
						for rr in lookup:
							requirelist.append(rr[2])
			requireds = ','.join(requirelist)
		requireds = fallback_email if requireds==None else requireds # in case something goes bad
	if no_requireds:						# if a direct VM (dial_extension)
		requireds = ''
	with app.app_context():						# pass the Flask app to the next function (weird rendering quirk)
		add_voicemail(recording_name, intent=intent, ani=ani, requireds=requireds, assigns=assign, caller_id=caller_id)
		send_email(recording_name, intent, ani, requireds, assign, caller_id=caller_id)
	#delete_file(recording_url)					# delete recording from Twilio
	return recording_name

def send_email(recording_name, intent, ani, requireds, assign, caller_id=None, app=app):
	'''send an email to the required and assigned recipients'''
	intent = str(intent)
	# look for configuration variables in params.conf file...
	msg = Message(sender=from_email)
	description = Intent.query.filter_by(digit=intent).first().description
	assign_names = " and ".join([a.split('@')[0].replace("."," ").title() for a in assign.split(',')]) # fancy :)
	msg.subject = assign_names + ' assigned EHHOP voicemail from ' + description + ", number " + ani		
	msg.sender  = from_email
	msg.recipients = assign.split(',') if ',' in assign else [assign]
	msg.cc = requireds.split(',') if ',' in requireds else [requireds]
	with app.app_context():
		msg.html = render_template('email.html', from_phone = ani, assign_names = assign_names, 
					playback_url = player_url + recordings_base + recording_name, desc = description, caller_id=caller_id)
		msg.body = render_template('email.txt', from_phone = ani, assign_names = assign_names, 
					playback_url = player_url + recordings_base + recording_name, desc = description, caller_id=caller_id)
	mail.send(msg)
	return None

def save_file(recording_url, auth_method):
	'''save a VM from twilio, pick a random name'''
	save_name = randomword(64) + ".mp3" # take regular name and salt it
										# we are now using HTTPS basic auth to do the downloads
										# step 0 - open up a FTP session with HIPAA box
	session = FTP_TLS('ftp.box.com', box_username, box_password)
										# step 1 - open a request to get the voicemail using a secure channel with Twilio
	response = requests.get(recording_url+".mp3", stream=True, auth=auth_method) 	# no data has been downloaded yet (just headers)
										# step 2 - read the response object in chunks and write it to the HIPAA box directly
	session.storbinary('STOR recordings/' + save_name, response.raw)

	response.close()										# step 3 - cleanup
	session.quit()
	del response
	return save_name

def save_file_with_name(recording_url, auth_method, save_name):
	'''save a VM from twilio, specify a filename, NOT USED'''
										# we are now using HTTP basic auth to do the downloads
										# step 0 - open up a FTP session with HIPAA box
	session = FTP_TLS('ftp.box.com', box_username, box_password)
										# step 1 - open a request to get the voicemail using a secure channel with Twilio
	response = requests.get(recording_url, stream=True, auth=auth_method) 	# no data has been downloaded yet (just headers)
										# step 2 - read the response object in chunks and write it to the HIPAA box directly
	session.storbinary('STOR recordings/' + save_name, response.raw)
	
	response.close()										# step 3 - cleanup
	session.quit()
	del response
	return save_name

def delete_file(recording_url):
	'''delete the recording from Twilio - IMPORTANT'''
	client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
	if "/" in recording_url:
		recording_sid = recording_url.split("/")[-1]
	if recording_sid in client.recordings.list():
		client.recordings.delete(recording_sid)
	return None

def randomword(length):
	'''generate a random string of whatever length, good for filenames'''
	return ''.join(random.choice(string.lowercase) for i in range(length))

def getSatDate():
	'''get next saturday's date - duplicate function!!!'''
        time_now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = time_now.weekday()
        addtime = None
        if day_of_week == 6:
                addtime=timedelta(6)
        else:
                addtime=timedelta(5-day_of_week)
        satdate = (time_now+addtime).strftime('%-m/%-d/%Y')
	return satdate

def getlastSatDate(time_now = None): # go Wed-Wed
	if time_now == None:
		time_now = datetime.now(pytz.timezone('US/Eastern'))
        # get next saturday's date for lookups in the schedule
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
