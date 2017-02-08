#!/usr/bin/python

#this would be a great place to upload the call logs to the server!! could be added to the crontab or via celerybeat

from twilio.rest import TwilioRestClient
from ehhapp_twilio.config import *
from ehhapp_twilio.email_helper import *

"""
Cleaner

It is meant to run periodically to delete call records from Twilio servers. 
A critical component for protecting patient privacy.

Requires:
    twilio_AccountSID, twilio_AuthToken
"""

record_sids = []
with open("/var/wsgiapps/ehhapp_twilio/download_log.txt", "r") as fp:
	for line in fp:
		record_sids.append(line.strip())

client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)

# step 1 - delete recordings (more of a catch-all)
recordings = client.recordings.list()
while len(recordings) > 0:
	for record in recordings:
		if int(record.duration) <=5:
			client.recordings.delete(record.sid)
			continue
		if record.sid not in record_sids:
			print "ERROR: Found recording left on server"
			print "to match: " + record.sid + " duration=" + str(record.duration)
			print "assigning now..."
			try:
				call = client.calls.get(record.call_sid)
				recording_name = process_recording(str('.'.join(record.formats['mp3'].split('.')[:-1])), 1, str(call.from_))
				with open("/var/wsgiapps/ehhapp_twilio/download_log.txt", "a") as fp:
        				fp.write(record.sid + "\n")
			except:
				raise Exception("Recording not in downloaded list. Automatic retry failed. Stop.")
				break
		client.recordings.delete(record.sid)
	#print "deleted recording"
	recordings = client.recordings.list()

# step 2 - delete call records
calls = client.calls.list()
while len(calls) > 0:
	for call in calls:
	# exclude in-progress or future calls
		if call.status not in ["queued", "ringing", "in-progress"]:
			client.calls.delete(call.sid)
			#print "deleted call"
	calls = client.calls.list()

# step 3 - delete transcriptions
transcriptions = client.transcriptions.list()
while len(transcriptions) > 0:
	for transcript in transcriptions:
		client.transcriptions.delete(transcript.sid)
		#print "deleted transcript"
	transcriptions = client.transcriptions.list()

# step 4 - delete SMS/MMS records
smses = client.messages.list()
while len(smses) > 0:
	for msg in smses:
		client.messages.delete(msg.sid)
		#print "deleted SMS"
	smses = client.messages.list()

