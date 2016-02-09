#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.config import *
from ehhapp_twilio.database import db_session
from ehhapp_twilio.models import Intent, Assignment

import smtplib, pytz, requests, random, string, re
from ftplib import FTP_TLS
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from requests.auth import HTTPBasicAuth
from twilio.rest import TwilioRestClient

from flask.ext.mail import Message

# user/pass to log into Twilio to retrieve files
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

def process_recording(recording_url, intent, ani, requireds=None, assign=None, no_requireds=False, auth_method=auth_combo):
	'''process_recording(recording_url, intent, ani, requireds=None, assign=None, auth_method=auth_combo)
	recording_url:	URL of recording to download
	intent:		the digit pressed by the caller
	ani: 		caller ID
	requireds:	(optional) override the default required recipients
	assign:		(optional) override the default assigned recipients
	no_requireds:	(optional) do not send emails to requireds even if passed
	auth_method:	(optional) specify different twilio REST API credentials
	'''

	satdate = getSatDate() # get next clinic date
	recording_name = save_file(recording_url, auth_method) # save the file

	# figure out who to send the message to
	if assign==None:
		db_assign = Assignment.query.filter_by(from_phone=ani[-10:]).all()
		if db_assign != []: #someone is responsible for that phone number
			assign = [a.recipients.replace(" ", "").split(',') for a in db_assign]
			assign = [item for sublist in assign for item in sublist] # flatten array of arrays
			assign = ','.join(assign)
		else: # no one has the default assignment for that phone number
			intent = Intent.query.filter_by(digit=intent).first()
			assigns = intent.distributed_recipients.split(',')
			assignlist = []
			db = EHHOPdb(credentials)
			for a in assigns:
				interresult = db.lookup_name_in_schedule(pos, satdate)
				for i in interresult:
					email = db.lookup_email_by_name(i)
					assignlist.append(email) if email != None else None
			counts = [Assignment.query.filter_by(recipients=a).count() for a in assignlist]
			assign = assignlist[counts.index(min(counts))] # gets whoever has the lowest load (alphabetical tiebreak)
			# save the new assignment to the database for later retrieval
			new_assign = Assignment(from_phone=ani[-10:], recipients=assign)
			db_session.add(new_assign)
			db_session.commit()
	if requireds==None and not no_requireds:
		db_requireds = Intent.query.filter_by(digit=intent).first()
		if db_requireds != None:
			requiredpos = db_requireds.split(',')
			requirelist = []
			for r in requiredpos:
				r = r.strip(" ")
				requirelist.append(db.lookup_name_by_position(r)[2])
			requireds = ','.join(requirelist)
		requireds = fallback_email if requireds==None else requireds # in case something goes bad
	if no_requireds:
		requireds = ''
	with app.app_context():
		send_email(recording_name, intent, ani, requireds, assign)
	delete_file(recording_url)
	return recording_name

def send_email(recording_name, intent, ani, requireds, assign):
	intent = str(intent)
	# look for configuration variables in params.conf file...
	msg = Message(sender=from_email)
	description = Intent.query.filter_by(digit=intent).first().description
	assign_names = ''
	if assign == None:
		msg.subject = 'TESTING - PLEASE IGNORE - EHHOP voicemail from ' + description + ", number " + ani
	else:
		assign_names = " and ".join([a.split('@')[0].replace("."," ").title() for a in assign.split(',')]) # fancy :)
		msg.subject = 'TESTING - PLEASE IGNORE - ' + assign_names + ' assigned EHHOP voicemail from ' + description + ", number " + ani
		
	msg.sender  = from_email
	msg.recipients = assign.split(',') if ',' in assign else [assign]
	msg.cc = requireds.split(',') if ',' in requireds else [requireds]
	msg.html = render_template('email.html', from_phone = ani, assign_names = assign_names, 
					playback_url = player_url + recordings_base + recording_name)
	msg.body = render_template('email.txt', from_phone = ani, assign_names = assign_names, 
					playback_url = player_url + recordings_base + recording_name)
	mail.send(msg)
	return None

def save_file(recording_url, auth_method):
	save_name = randomword(64) + ".wav" # take regular name and salt it
	# we are now using HTTP basic auth to do the downloads
	# step 0 - open up a FTP session with HIPAA box
	session = FTP_TLS('ftp.box.com', box_username, box_password)
	# step 1 - open a request to get the voicemail using a secure channel with Twilio
	response = requests.get(recording_url, stream=True, auth=auth_method) # no data has been downloaded yet (just headers)
	# step 2 - read the response object in chunks and write it to the HIPAA box directly
	session.storbinary('STOR recordings/' + save_name, response.raw)
	# step 3 - cleanup
	session.quit()
	del response
	return save_name

def save_file_with_name(recording_url, auth_method, save_name):
	# we are now using HTTP basic auth to do the downloads
	# step 0 - open up a FTP session with HIPAA box
	session = FTP_TLS('ftp.box.com', box_username, box_password)
	# step 1 - open a request to get the voicemail using a secure channel with Twilio
	response = requests.get(recording_url, stream=True, auth=auth_method) # no data has been downloaded yet (just headers)
	# step 2 - read the response object in chunks and write it to the HIPAA box directly
	session.storbinary('STOR recordings/' + save_name, response.raw)
	# step 3 - cleanup
	session.quit()
	del response
	return save_name

def delete_file(recording_url):
	# delete the recording from Twilio - IMPORTANT
	client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
	if "/" in recording_url:
		recording_sid = recording_url.split("/")[-1]
	if recording_sid in client.recordings.list():
		client.recordings.delete(recording_sid)
	return None

def randomword(length):
	return ''.join(random.choice(string.lowercase) for i in range(length))

def getSatDate():
	# get next saturday's date
        time_now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = time_now.weekday()
        addtime = None
        if day_of_week == 6:
                addtime=timedelta(6)
        else:
                addtime=timedelta(5-day_of_week)
        satdate = (time_now+addtime).strftime('%m/%d/%Y')
	return satdate

