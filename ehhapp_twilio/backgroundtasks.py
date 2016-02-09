from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.email_helper import *

from celery import Celery

#pass flask to celery when background tasks are run
def make_celery(app):
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
	name = process_recording(recording_url, intent, ani, requireds=requireds, 
							     assign=assign, 
							     no_requireds=no_requireds)
	return name

@celery.task
def save_secure_message(recording_url, save_name):
	# download the file to HIPAA box
	save_file_with_name(recording_url, auth_combo, save_name)
	return None

@celery.task
def send_message(remind_id, to_phone):
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/callback/" + str(remind_id),
		to = to_phone,
		from_ = twilio_number,
	)
	return None

@celery.task
def deliver_callback(remind_id, from_phone):
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/delivered/" + str(remind_id),
		to = from_phone,
		from_ = twilio_number,
	)
	return None

#==============other helpers===========

def set_async_message_deliver(record, remind_id):
	deliver_time = datetime.strptime(record.time,'%Y-%m-%d %H:%M:%S.%f')
	send_message.apply_async(args=[remind_id, record.to_phone], eta=deliver_time)	
	return None


