import dataset
import sys, os, pytz, re, ftplib
from datetime import datetime, timedelta, date, time
from SOAPpy import WSDL
from flask import Flask, request, redirect, send_from_directory, Response, stream_with_context
import twilio.twiml
from celery import Celery

base_dir = os.path.dirname(os.path.realpath(__file__))
execfile(base_dir + "/gdatabase.py")
execfile(base_dir + "/email_helper.py")

from twilio.rest import TwilioRestClient
client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)

wsdlfile='http://phone.ehhapp.org/services.php?wsdl'

app = Flask(__name__, static_folder='')
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
app.debug = True

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# user/pass to log into Twilio to retrieve files
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

@app.route('/', methods=['GET', 'POST'])
def hello_ehhop():
	'''respond to incoming requests:'''
	
	#Gracias por llamar a la Clinica de EHHOP. 
	#Para instrucciones en espanol, marque el numero 2. 
	#Thank you for calling the EHHOP clinic. 
	#If this is an emergency please 
	#hang up and dial 9 1 1 now.
	#For instructions in English, please press 1.
	#If you know your party's extension, please press #.
	#EHHOP es la Asociacion Comunitaria para la Salud de 
	#East Harlem en Mount Sinai. Si esto es una emergencia, 
	#cuelgue el telefono y llame ahora al 9-1-1. We are the 
	#East Harlem Health Outreach Partnership of the Icahn School 
	#of Medicine at Mount Sinai. 

	resp = twilio.twiml.Response()
	with resp.gather(numDigits=1, action="/handle_key/hello", method="POST") as g:
		for i in range(0,3):
			g.play("https://s3.amazonaws.com/ehhapp-phone/welcome_greeting_ehhop.mp3")
			g.pause(length=5)
	return str(resp)

@app.route("/handle_key/hello", methods=["GET", "POST"])
def handle_key_hello():
	'''respond to initial direction'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)
	#get day of week (0 is Monday and 6 is Sunday)
	day_of_week = datetime.now(pytz.timezone('US/Eastern')).weekday()
		
	if digit == '1':
		'''instructions in english selected'''
		if day_of_week == 5: #clinic is open on Saturdays
			with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
				
				#If you have an appointment today, please press 1. 
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				for i in range(0,3):
					g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
					g.pause(length=5)
		else:
			with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g:
				
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				for i in range(0,3):
					g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3")
					g.pause(length=5)
					
	elif digit == '2':
		'''instructions in spanish selected'''
		# spanish: if this is an emerg, dial 911
		resp.play('https://s3.amazonaws.com/ehhapp-phone/sp_emerg_911.mp3')
		if day_of_week == 5: #clinic is open on Saturdays
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
				# spanish: list options 1-4 similar to english
				for i in range(0,3):
					g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
					g.pause(length=5)
		else: #clinic not open
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g:
				# spanish: list options 2-4 similar to english
				for i in range(0,3):
					g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_closed_menu.mp3')
					g.pause(length=5)
	elif digit == "3": 
		'''extension feature'''
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.say("Please dial your four digit extension now.", voice='alice', language="en-US")
		
	elif digit == '*':
		'''auth menu'''
		with resp.gather(numDigits=8, action='/auth_menu', method="POST") as g:
			g.say("Please enter your passcode.", voice='alice')
	
	else:
		'''They have pressed an incorrect key.'''
		return redirect('/')
	
	return str(resp)

@app.route("/dial_extension", methods=["GET", "POST"])
def dial_extension():
	resp = twilio.twiml.Response()
	digits = request.values.get('Digits', None)
	database = EHHOPdb(credentials)
	try:
		return_num = database.lookup_phone_by_extension(int(digits))
	except:
		resp.say("I'm sorry, I couldn't find that extension.")
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.say("Please dial your four digit extension now.", voice='alice', language="en-US")
		return str(resp)
	if return_num == None:
		resp.say("I'm sorry, I couldn't find that extension.")
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.say("Please dial your four digit extension now.", voice='alice', language="en-US")
	else:
		resp.say("Connecting you with " + return_num[0], voice='alice', language='en-US')
		resp.pause(length=3)
		resp.dial(return_num[1], callerId='+18622425952')
		resp.say("I'm sorry, but your call either failed or may have been cut short. Goodbye!", voice='alice', language='en-US')
	return str(resp)

@app.route("/next_clinic/<person_type>/", methods=["GET", "POST"])
def find_in_schedule(person_type):
	resp = twilio.twiml.Response()
	database = EHHOPdb(credentials)
	return_num = None
	try:
		return_names = database.lookup_name_in_schedule(person_type, getSatDate())
		if return_names != []:
			return_num = database.lookup_phone_by_name(return_names[0])
	except:
		resp.say("I'm sorry, please try your lookup again later.")
		return str(resp)
		
	if return_names == []:
		resp.say("I'm sorry, I couldn't find that person.")
	else:
		for name in return_names:
			return_num = database.lookup_phone_by_name(name)
			if return_num != None:
				resp.say("Connecting you with " + name, voice='alice', language='en-US')
				resp.pause(length=3)
				resp.dial(return_num, callerId='+18622425952')
		resp.say("I'm sorry, but your call either failed or may have been cut short. Goodbye!", voice='alice', language='en-US')
	return str(resp)

@app.route("/find_person/<person_type>/", methods=["GET", "POST"])
def find_person(person_type):
        resp = twilio.twiml.Response()
        database = EHHOPdb(credentials)
        return_num = None
        try:
                return_nums = database.lookup_name_by_position(person_type)      
        except:
                resp.say("I'm sorry, please try your lookup again later.")
                return str(resp)

        if return_num == []:
                resp.say("I'm sorry, I couldn't find that person.")
        else:
                for return_num in return_nums:
                        if return_num != None:
                                resp.say("Connecting you with " + return_num[0], voice='alice', language='en-US')
                                resp.pause(length=3)
                                resp.dial(return_num[1], callerId='+18622425952')
                resp.say("I'm sorry, but your call either failed or may have been cut short. Goodbye!", voice='alice', language='en-US')
        return str(resp)
	
@app.route("/handle_key/clinic_open_menu", methods=["GET", "POST"])
def clinic_open_menu():
	'''respond to digit press when the clinic is open
	1 - appt today
	2 - not been here before
	3 - urgent concern and ehhop patient
	4 - ehhop pt with question
	'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)

	# get the phone # of the on call - fallback if something wrong
	oncall_current_phone = getOnCallPhoneNum()

	# appointment today
	if digit == '1':
		# now transferring your call
		resp.play("https://s3.amazonaws.com/ehhapp-phone/xfer_call.mp3")
		# dial current CM
		resp.dial(oncall_current_phone)
		# if the call fails
		resp.say("All clinicians are busy at the moment. Please try again.", voice='alice', language='en-US')
		# replay initial menu
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
				#If you have an appointment today, please press 1. 
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
				g.pause(length=5)
	# not been here before
	elif digit in ['2', '3', '4']:
		return redirect('/take_message/' + digit)
	# accidential key press
	else:
		resp.say("I'm sorry, but you have pressed an incorrect key.", voice='alice', language='en-US')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
			#If you have an appointment today, please press 1. 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about medications, appointments, 
			#or other matters, please press 4.
			g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
			g.pause(length=5)
	return str(resp)

@app.route("/handle_key/clinic_closed_menu", methods=["GET", "POST"])
def clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)
	
	if intent in ['2','3','4']:
		return redirect("/take_message/" + intent)
	else:
		resp.say("I'm sorry, but you have pressed an incorrect key.", voice='alice', language='en-US')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g: 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about medications, appointments, 
			#or other matters, please press 4.
			g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3")
			g.pause(length=5)
	return str(resp)
	
@app.route("/take_message/<intent>", methods=['GET', 'POST'])
def take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	
	resp = twilio.twiml.Response()
	
	if intent == '3':
		#Please leave a message for us after the tone. We will call you back as soon as possible.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/urgent_message.mp3")
	if intent in ['2','4']:
		#Please leave a message for us after the tone. We will call you back within one day.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/nonurgent_message.mp3")

	resp.play("https://s3.amazonaws.com/ehhapp-phone/vm_instructions.mp3")

	# after patient leaves message, direct them to next step
	after_record = '/handle_recording/' + intent
	resp.record(maxLength=300, action=after_record, method="POST")	

	return str(resp)

@app.route("/handle_recording/<int:intent>", methods=['GET', 'POST'])
def handle_recording(intent):
	'''patient has finished leaving recording'''
	resp = twilio.twiml.Response()
	ani = request.values.get('From', 'None')
	recording_url = request.values.get("RecordingUrl", None)

	# process message asynchronously (e.g. download and send emails) using Celery
	async_process_message.delay(recording_url, intent, ani)

	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sent_message.mp3")
	return str(resp)

################# spanish path ###############

@app.route("/handle_key/sp/clinic_open_menu", methods=["GET", "POST"])
def sp_clinic_open_menu():
	'''respond to digit press when the clinic is open
	1 - appt today
	2 - not been here before
	3 - urgent concern and ehhop patient
	4 - ehhop pt with question
	'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)
	
	# get the phone # of the on call - fallback if something wrong
	oncall_current_phone = getOnCallPhoneNum()
	
	# appointment today
	if digit == '1':
		# now transferring your call
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_xfer_call.mp3")
		# dial current CM
		resp.dial(oncall_current_phone)
		# if the call fails
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_try_again.mp3")
		# replay initial menu
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
			# spanish: list options 1-4 similar to english
			for i in range(0,3):
				g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
				g.pause(length=5)
	# not been here before
	elif digit in ['2', '3', '4']:
		return redirect('/sp/take_message/' + digit)
	# accidential key press
	else:
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_incorrect_key.mp3")
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
			# spanish: list options 1-4 similar to english
			for i in range(0,3):
				g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
				g.pause(length=5)
	return str(resp)

@app.route("/handle_key/sp/clinic_closed_menu", methods=["GET", "POST"])
def sp_clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)
	
	if intent in ['2','3','4']:
		return redirect("/sp/take_message/" + intent)
	else:
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_incorrect_key.mp3")
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g:
			# spanish: list options 2-4 similar to english
			for i in range(0,3):
				g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_closed_menu.mp3')
				g.pause(length=5)
	return str(resp)
	
@app.route("/sp/take_message/<intent>", methods=['GET', 'POST'])
def sp_take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	
	resp = twilio.twiml.Response()
	
	if intent == '3':
		#spanish: Please leave a message for us after the tone. We will call you back as soon as possible.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_urgent_message.mp3")
	if intent in ['2','4']:
		#spanish: Please leave a message for us after the tone. We will call you back within one day.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_nonurgent_message.mp3")
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_vm_instructions.mp3")

	# save recording after received at next step
	after_record = '/sp/handle_recording/' + intent
	resp.record(maxLength=300, action=after_record, method="POST")
	
	return str(resp)

@app.route("/sp/handle_recording/<int:intent>", methods=['GET', 'POST'])
def sp_handle_recording(intent):
	'''patient has finished leaving recording'''
        resp = twilio.twiml.Response()
        ani = request.values.get('From', 'None')
        recording_url = request.values.get("RecordingUrl", None)

        # process message (e.g. download and send emails)
	async_process_message.delay(recording_url, intent, ani)
	
	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_sent_message.mp3")
	return str(resp)

#==============SERVE VOICEMAILS============

@app.route('/play_recording', methods=['GET', 'POST'])
def play_vm_recording():
	''' plays a voicemail recording from the Box server'''
	filename = request.values.get('filename', None)
	# check that filename attribute was set, else return None
	if filename == None:
		return "Need to specify a filename.", 400

	# sterilize filename to prevent attacks
	safe_char = re.compile(r'[^\w.]+') # only alphanumeric and periods
	filename = safe_char.sub('', filename)
	
	def get_file(filename):
		# get file
		chunks = []
		session = ftplib.FTP('ftp.box.com', box_username, box_password)
		session.retrbinary('RETR recordings/' + filename, chunks.append)
		session.close()
		for chunk in chunks:
			yield chunk
	
	# serve file
	return Response(get_file(filename), mimetype='audio/wav')

#==============authenticated menu============
@app.route("/auth_menu", methods=['GET','POST'])
def auth_menu():
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)
	
	if passcode == '12345678':
		#success
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			g.say("To dial a patient using the EHHOP number, please press 1. To leave a secure message for a patient, please press 2.", voice='alice')
		return str(resp)
	else:
		resp.say("I'm sorry, that passcode is incorrect.", voice='alice')
		with resp.gather(numDigits=8, action='/auth_menu', method='POST') as g:
			g.say("Please enter your passcode.", voice='alice')
		return str(resp)

@app.route("/auth_selection", methods=['GET','POST'])
def auth_selection():
	resp = twilio.twiml.Response()
	digit = request.values.get("Digits", None)

	if digit == '1':
		with resp.gather(numDigits=10, action='/caller_id_dial', method='POST') as g:
			g.say("Please enter the ten-digit phone number you wish to call, starting with the area code", voice='alice')
		return str(resp)
	elif digit == '2':
		with resp.gather(numDigits=10, action='/secure_message/setnum/', method='POST') as g:
			g.say("Please enter the ten-digit phone number you wish to send a message to, starting with the area code", voice='alice')
		return str(resp)
	else:
		resp.say("I didn't catch that.")
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			g.say("To dial a patient using the EHHOP number, please press 1. To leave a secure message for a patient, please press 2.", voice='alice')
                return str(resp)

@app.route("/secure_message/setnum/", methods=['GET', 'POST'])
def secure_message_setnum():
	''' creates a row in the database with a secure message ID and pt phone num
	    still need to set the following:
		reminder time (now, one day from now, or specify date)
		reminder frequency (default = one day if they dont pick up)
		message
		recorded name
		spanish?
		passcode
	'''
	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)
	from_phone=request.values.get("From", None)
	
	db = open_db()	
	r = db['reminders']
	# add phone number to reminders, move to next step
	remind_id = r.insert(dict(to_phone=number, 
			from_phone=from_phone,
			time=None,
			freq=24,
			message=None,
			name=None,
			passcode=None,
			spanish=None))
	
	with resp.gather(numDigits=6, action='/secure_message/setpass/' + str(remind_id), method='POST') as g:
		g.say("You dialed " + ' '.join(number) + '. ', voice='alice')
		g.say("Please enter the patient's date of birth, using two digits for the month, day, and year.")
	return str(resp)

@app.route("/secure_message/setpass/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_setpass(remind_id):
	''' sets the passcode from the last step and asks for a reminder time '''
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']

	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.say("I am sorry, but I could not find a record in the database that matched that ID.")
		return str(resp)

	# set a passcode and update the DB
	record['passcode'] = passcode
	r.update(record, ['id'])

	# ask for a reminder time
	with resp.gather(numDigits=1, action='/secure_message/settime/' + str(remind_id), method='POST') as g:
		g.say("You dialed " + ' '.join(passcode) + ".", voice="alice")
		g.say("To send your message now, please press 1. To send your message tomorrow morning at 10 AM, please press 2.")
	return str(resp)

@app.route("/secure_message/settime/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_settime(remind_id):
	''' sets the reminder time and asks for the message '''
	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.say("I am sorry, but I could not find a record in the database that matched that ID.")
		return str(resp)
	
	# set the reminder time delta
	nowtime = datetime.now()
	time_set = None
	if choice == '2':
		# set the time for tomorrow
		time_set = datetime.combine(nowtime.date() + timedelta(1), time(10,0,0,1))
	else:
		# set the time as now
		time_set = nowtime
	
	# set the reminder time and update the DB
	record['time'] = str(time_set)
        r.update(record, ['id'])
	
	# now we need to record the message
	resp.say("Please leave your secure message after the tone, and press any number and hold as we process your message.")
	resp.record(maxLength=300, action="/secure_message/setmessage/" + str(remind_id), method='POST')

	return str(resp)

@app.route("/secure_message/setmessage/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_setmessage(remind_id):
	resp = twilio.twiml.Response()
	recording_url = request.values.get("RecordingUrl", None)
	
	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.say("I am sorry, but I could not find a record in the database that matched that ID.")
		return str(resp)

	# download the file to HIPAA box
	save_name = save_file(recording_url, auth_combo)
	# set the secure recording URL location
	new_recording_url = 'https://twilio.ehhapp.org/play_recording?filename=' + save_name

	# set the message url and update the db
	record['message'] = new_recording_url
        r.update(record, ['id'])	

	with resp.gather(numDigits=1, action='/secure_message/send/' + str(remind_id), method='POST') as g:
		g.say("Thank you. To confirm your secure message, press 1 at any time, otherwise hang up now. ")
		g.say('Here is your secure message.')
		g.play(new_recording_url)
	return str(resp)

@app.route("/secure_message/send/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_send(remind_id):
	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.say("I am sorry, but I could not find a record in the database that matched that ID.")
		return str(resp)
	
	# we should have everything now, so make a record in celery for a call out
	set_async_message_deliver(record, remind_id)
	
	resp.say("Thank you. Your secure message has been sent and will be delivered soon. Goodbye!")
	return str(resp)

@app.route("/secure_message/callback/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_callback(remind_id):
	resp = twilio.twiml.Response()

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.say("Hello! You have an important message waiting for you from the EHHOP Clinic at Mount Sinai.")
		resp.say("Please call EHHOP at 862-242-5952 to hear your message.")
		return str(resp)
	
	with resp.gather(numDigits=1, action='/secure_message/passauth/' + str(remind_id), method='POST') as g:
		g.say("Hello! You have an important message waiting for you from the e hop Clinic at Mount Sinai Hospital.")
		g.say("Press any number to hear your message.")
	return str(resp)		

@app.route("/secure_message/passauth/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_passauth(remind_id):
	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.say("We're sorry, but your message cannot be retrieved at this time.")
		resp.say("Please call EHHOP at 862-242-5952 to hear your message.")
		return str(resp)

	with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
		g.say("Please enter your date of birth, using two digits for the month, day, and year")
		g.say("For instance, if your birthday is January 5th, 1980, then you would type 0 1, 0 5, 8 0.")
	return str(resp)

@app.route("/secure_message/playback/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_playback(remind_id):
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	# find the record in the DB that corresponds to this call
	record = r.find_one(id=remind_id)
	
	if record['passcode'] != passcode:
		with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
			g.say("We're sorry, but your passcode is incorrect.")
			g.say("Please enter your date of birth, using two digits for the month, day, and year")
		return str(resp)
	else:
		deliver_callback.apply_async(args=[remind_id, record['from_phone']], eta=datetime.now())
		resp.say("Please wait to hear your secure message from EHHOP.")
		resp.play(record['message'])
		resp.say("Your message will be repeated now.")
		resp.play(record['message'], loop=5)
		resp.say("Thank you for coming to the e hop clinic. Goodbye!")
		return str(resp)

@app.route("/secure_message/delivered/<int:remind_id>", methods=["GET", "POST"])
def secure_message_delivered(remind_id):
	resp = twilio.twiml.Response()

	db = open_db()
	r = db['reminders']
	# find the record in the DB that corresponds to this call
	record = r.find_one(id=remind_id)
	
	resp.say("Hello! This is a notification from the e hop secure message delivery system. ")
	resp.say("Your secure message to the number " + ' '.join(record["to_phone"]) + " was delivered sucessfully. Goodbye!")
	return str(resp)


@app.route("/caller_id_dial", methods=['GET','POST'])
def caller_id_dial():
	''' dials out from the EHHOP phone number'''

	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)

	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.say("If you would like to try again, please press 1, otherwise, hang up now.", voice='alice', language='en-US')
	return str(resp)
	
@app.route("/caller_id_redial/<number>", methods=['GET','POST'])
def caller_id_redial(number):
	'''redials a number dialed out by caller_id_dial - digits only dialed once'''

	resp = twilio.twiml.Response()
	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.say("If you would like to try again, please press 1, otherwise, hang up now.", voice='alice', language='en-US')
	return str(resp)

#==============OTHER HELPERS===============

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

def getOnCallPhoneNum():
	# get next saturday's date
	satdate = getSatDate()

	# get the phone # of the on call - fallback if something wrong
	try:
	        server = WSDL.Proxy(wsdlfile)
        	oncall_phone_unsan = server.get_oncall_CM_phone(nearest_saturday=satdate).strip('-')
	        d = re.compile(r'[^\d]+')
        	oncall_current_phone = '+1' + d.sub('', oncall_phone_unsan)
	except:
		oncall_current_phone = fallback_phone
	return oncall_current_phone

def open_db():
	db = dataset.connect('sqlite:///var/wsgiapps/ehhapp-twilio/ehhapp-twilio.db')
	return db

#==============BACKGROUND TASKS==============
@celery.task
def async_process_message(recording_url, intent, ani):
	process_recording(recording_url, intent, ani)
	return None

def set_async_message_deliver(record, remind_id):
	deliver_time = datetime.strptime(record['time'],'%Y-%m-%d %H:%M:%S.%f')
	send_message.apply_async(args=[remind_id, record['to_phone']], eta=deliver_time)	
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

#============MUST BE LAST LINE================
if __name__ == '__main__':
	app.debug = True
	app.run()

