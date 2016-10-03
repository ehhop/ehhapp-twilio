#!/usr/bin/python

#this would be a great place to upload the call logs to the server!! could be added to the crontab or via celerybeat

from twilio.rest import TwilioRestClient
from ehhapp_twilio.config import *

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
for record in recordings:
	if record.sid not in record_sids:
		raise Exception("Recording not in downloaded list. Stop.")
		break
	client.recordings.delete(record.sid)
	#print "deleted recording"

# step 2 - delete call records
calls = client.calls.list()
for call in calls:
	# exclude in-progress or future calls
	if call.status not in ["queued", "ringing", "in-progress"]:
		client.calls.delete(call.sid)
		#print "deleted call"

# step 3 - delete transcriptions
transcriptions = client.transcriptions.list()
for transcript in transcriptions:
	client.transcriptions.delete(transcript.sid)
	#print "deleted transcript"

# step 4 - delete SMS/MMS records
smses = client.messages.list()
for msg in smses:
	client.messages.delete(msg.sid)
	#print "deleted SMS"
