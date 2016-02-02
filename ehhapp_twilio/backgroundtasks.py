from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from celery import Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task(name='tasks.async_process_message')
def async_process_message(recording_url, intent, ani, positions, to_emails=None):
	process_recording(recording_url, intent, ani, positions, to_emails=to_emails)
	return None

def set_async_message_deliver(record, remind_id):
	deliver_time = datetime.strptime(record['time'],'%Y-%m-%d %H:%M:%S.%f')
	send_message.apply_async(args=[remind_id, record['to_phone']], eta=deliver_time)	
	return None

@celery.task
def save_secure_message(recording_url, save_name):
	# download the file to HIPAA box
	save_file_with_name(recording_url, auth_combo, save_name)
	return None

@celery.task
def send_message(remind_id, to_phone):
	execfile(base_dir + "/gdatabase.py")
	execfile(base_dir + "/email_helper.py")
	from twilio.rest import TwilioRestClient
	client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/callback/" + str(remind_id),
		to = to_phone,
		from_ = twilio_number,
	)
	return None

@celery.task
def deliver_callback(remind_id, from_phone):
	execfile(base_dir + "/gdatabase.py")
	execfile(base_dir + "/email_helper.py")
	from twilio.rest import TwilioRestClient
	client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/delivered/" + str(remind_id),
		to = from_phone,
		from_ = twilio_number,
	)
	return None
