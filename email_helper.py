import pytz, smtplib, requests, shutil, random, string, re, os, ftplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from requests.auth import HTTPBasicAuth
from twilio.rest import TwilioRestClient

execfile("/var/wsgiapps/ehhapp-twilio/params.conf")
base_dir = "/var/wsgiapps/ehhapp-twilio"

# user/pass to log into Twilio to retrieve files
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

def process_recording(recording_url, intent, ani, auth_method=auth_combo):
	satdate = getSatDate()
	recording_name = save_file(recording_url, auth_method)
	send_email(recording_name, intent, ani)
	delete_file(recording_url)
	return None

def send_email(recording_name, intent, ani):
	intent = str(intent)
	# look for configuration variables in params.conf file...
	msg = MIMEText(email_template % (player_url + recordings_base + recording_name, from_email))
	msg['Subject'] = 'EHHOP voicemail from ' + intentions[intent] + ", number " + ani
	msg['From']  = from_email
	msg['To'] = ','.join(it_emails)

	s = smtplib.SMTP('localhost')
	s.sendmail(from_email, it_emails, msg.as_string())
	s.quit()
	return None

def save_file(recording_url, auth_method):
	save_name = randomword(128) + ".wav" # hopefully no collisions
	# we are now using HTTP basic auth to do the downloads
	# step 0 - open up a FTP session with HIPAA box
	session = ftplib.FTP('ftp.box.com', box_username, box_password)
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
	recording_sid = recording_url.split("/")[-1]
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


