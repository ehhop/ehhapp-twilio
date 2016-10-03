from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.email_helper import *
from celery import Celery, Task

def make_celery(app):
	'''pass flask to celery when background tasks are run'''
	celery = Celery(app.name)
	celery.config_from_object("celeryconfig")
	TaskBase = celery.Task
	class ContextTask(TaskBase):
		abstract = True
		def __call__(self, *args, **kwargs):
			with app.app_context():
				return TaskBase.__call__(self, *args, **kwargs)
	celery.Task = ContextTask
	return celery

#init celery
celery = make_celery(app)

@celery.task(name='tasks.async_process_message')
def async_process_message(recording_url, intent, ani, requireds=None, assign=None, no_requireds=False):
	'''background download a VM message, send emails, etc.'''
	name = process_recording(recording_url, intent, ani, requireds=requireds, 
							     assign=assign,
							     no_requireds=no_requireds)
	## example = https://api.twilio.com/2010-04-01/Accounts/ACb9eae62a9e303d8cf34f5c3d3d6fa020/Recordings/REd45318fa30bcdbdad533df02c57e2c95.wav
	record_sid = recording_url.split("/")[-1].split(".")[0]
	with open("/var/wsgiapps/ehhapp_twilio/download_log.txt", "a") as fp:
		fp.write(record_sid + "\n")
	return name #randomly-generated name

@celery.task
def save_secure_message(recording_url, save_name):
	'''background download a VM file to HIPAA box without sending an email'''
	save_file_with_name(recording_url, auth_combo, save_name)
	return None

# Send secure message feature, may or may not release in first launch
@celery.task
def send_message(remind_id, to_phone):
	'''background send a secure message at a certain time'''
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/callback/" + str(remind_id),
		to = to_phone,
		from_ = twilio_number,
	)
	return None

@celery.task
def deliver_callback(remind_id, from_phone):
	'''background deliver a callback when a secure message is sent while patient is on the phone still (or afterwards)'''
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/delivered/" + str(remind_id),
		to = from_phone,
		from_ = twilio_number,
	)
	return None

#==============other helpers===========

def set_async_message_deliver(record, remind_id):			# not a background task
	'''helper function that schedules the background task to run at time specified by the view (english_path.py)'''
	deliver_time = datetime.strptime(record.time,'%Y-%m-%d %H:%M:%S.%f')
	send_message.apply_async(args=[remind_id, record.to_phone], eta=deliver_time)	
	return None


