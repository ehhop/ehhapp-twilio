import smtplib
from email.mime.text import MIMEText
import requests
import shutil
import random, string
execfile("/var/wsgiapps/ehhapp-twilio/params.conf")
base_dir = "/var/wsgiapps/ehhapp-twilio"

def send_email(recording_url, intent, ani, satdate):
	intent = str(intent)
        save_name = randomword(128) + ".wav" # hopefully no collisions
        response = requests.get(recording_url, stream=True)
        with open(base_dir + "/recordings/" + save_name, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
        del response

	msg = MIMEText(email_template % (player_url + recordings_base + save_name, from_email))
	msg['Subject'] = 'EHHOP voicemail from ' + intentions[intent] + ", number " + ani
	msg['From']  = from_email
	msg['To'] = ','.join(it_emails)

	s = smtplib.SMTP('localhost')
	s.sendmail(from_email, it_emails, msg.as_string())
	s.quit()

def randomword(length):
   return ''.join(random.choice(string.lowercase) for i in range(length))
