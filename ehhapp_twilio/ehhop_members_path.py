#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.backgroundtasks import *
from ehhapp_twilio.database import db_session
from ehhapp_twilio.models import Reminder

@app.route("/auth_menu", methods=['GET','POST'])
def auth_menu():
	'''after they press * on main menu - deliver options'''
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)
	
	if passcode == '12345678':
		#success
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			#To call Pacific Interpreters, please press 1.
			#To dial a patient using the ehhop number, please press 2.
			#To leave a secure message for a patient, please press 3. 			
			g.play('/assets/audio/dial-vmremindermenu.mp3')
		return str(resp)
	else:
		resp.play('/assets/audio/incorrectkey.mp3')
		with resp.gather(numDigits=8, action='/auth_menu', method='POST') as g:
			g.play('/assets/audio/enterpasscode.mp3')
		return str(resp)

@app.route("/auth_selection", methods=['GET','POST'])
def auth_selection():
	'''made a selection from auth menu function, now handle it'''
	resp = twilio.twiml.Response()
	digit = request.values.get("Digits", None)
	
	if digit == '1':						# pacific interpreters
		with resp.dial(callerId='+18773724161') as n:
			n.number(number='+18002641552', sendDigits="wwwwww828099#")
		return str(resp)
	elif digit == '2':						# use EHHOP caller ID
		with resp.gather(numDigits=10, action='/caller_id_dial', method='POST') as g:
			g.play('/assets/audio/entertodigits.mp3')
		return str(resp)
	elif digit == '3':						# leave secure message
		with resp.gather(numDigits=10, action='/secure_message/setnum/', method='POST') as g:
			g.play('/assets/audio/entertendigits-vm.mp3')
		return str(resp)
	elif digit == '4':
		db = EHHOPdb(credentials)
		TS  = db.lookup_name_in_schedule('On Call Medical Clinic TS', getlastSatDate())
		num = db.lookup_phone_by_name(TS[0])
		resp.play("Transferring to on call TS.")
		resp.dial(num)
		return str(resp)
	else:								# incorrect key
		resp.play('/assets/audio/incorrectkey.mp3')
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			g.play('/assets/audio/dial-vmremindermenu.mp3')
                return str(resp)

@app.route("/secure_message/setnum/", methods=['GET', 'POST'])
def secure_message_setnum():						# start secure message function
	''' creates a row in the database with a secure message ID and pt phone num
	    still need to set the following:
		reminder time (now, one day from now, or specify date)
		reminder frequency (default = one day if they dont pick up)
		message
		recorded name
		spanish?
		passcode
	'''
	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)
	from_phone=request.values.get("From", None)
	
	
	# add phone number to reminders, move to next step
	reminder = Reminder(to_phone=number, from_phone=from_phone)
	db_session.add(reminder)
	db_session.commit()
	remind_id = reminder.id
	
	with resp.gather(numDigits=6, action='/secure_message/setpass/' + str(remind_id), method='POST') as g:
		g.play('/assets/audio/youdialed.mp3')
		g.say(' '.join(number) + '. ', voice='alice')
		g.play('/assets/audio/setpass.mp3')
	return str(resp)

@app.route("/secure_message/setpass/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_setpass(remind_id):					# second step in secure message
	''' sets the passcode from the last step and asks for a reminder time '''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)

	try:
		# find the record in the DB that corresponds to this call
		record = Reminder.query.get(remind_id)
	except:
		resp.play('/assets/audio/vmsystemfail.mp3')
		return str(resp)

	# set a passcode and update the DB
	record.passcode = passcode
	db_session.add(record)
	db_session.commit()

	# ask for a reminder time
	with resp.gather(numDigits=1, action='/secure_message/settime/' + str(remind_id), method='POST') as g:
		g.play('/assets/audio/youdialed.mp3')
		g.say(' '.join(passcode) + ".", voice="alice")
		g.play('/assets/audio/settime.mp3')
	return str(resp)

@app.route("/secure_message/settime/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_settime(remind_id):					# third step in secure message
	''' sets the reminder time and asks for the message '''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	try:
		# find the record in the DB that corresponds to this call
		record = Reminder.query.get(remind_id)
	except:
		resp.play('/assets/audio/vmsystemfail.mp3')
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
	record.time = str(time_set)
        db_session.add(record)
	db_session.commit()
	
	# now we need to record the message
	resp.play('/assets/audio/leavesecuremessage.mp3')
	resp.record(maxLength=300, action="/secure_message/setmessage/" + str(remind_id), method='POST')

	return str(resp)

@app.route("/secure_message/setmessage/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_setmessage(remind_id):				# fourth step in secure message - record the message
	'''record secure message'''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	recording_url = request.values.get("RecordingUrl", None)

	try:
		# find the record in the DB that corresponds to this call
		record = Reminder.query.get(remind_id)
	except:
		resp.play('/assets/audio/vmsystemfail.mp3')
		return str(resp)

	# set a new save file name randomly
	save_name = randomword(128) + ".mp3"
	# set the secure recording URL location
	new_recording_url = 'https://twilio.ehhapp.org/play_recording?filename=' + save_name
	# set the message url and update the db
	record.message = new_recording_url
        db_session.add(record)
	db_session.commit()

	# download and save the message (async)
	save_secure_message.apply_async(args=[recording_url, save_name])

	with resp.gather(numDigits=1, action='/secure_message/send/' + str(remind_id), method='POST') as g:
		g.play('/assets/audio/confirmsecuremessage.mp3')
	return str(resp)

@app.route("/secure_message/send/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_send(remind_id):					# confirm messsage to send
	'''after leaving VM, confirm to send it'''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	try:
		# find the record in the DB that corresponds to this call
		record = Reminder.query.get(remind_id)
	except:
		resp.play('/assets/audio/vmsystemfail.mp3')
		return str(resp)
	
	# we should have everything now, so make a record in celery for a call out
	set_async_message_deliver(record, remind_id)
	
	resp.play('/assets/audio/securemessagesent.mp3')
	return str(resp)

@app.route("/secure_message/callback/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_callback(remind_id):					# gets run when patient is called
	'''callback function for when we dial out to patient'''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()

	try:
		# find the record in the DB that corresponds to this call
		record = Reminder.query.get(remind_id)
	except:
		resp.play('/assets/audio/hello_importantmessage.mp3')
		resp.play('/assets/audio/messageretrievalfail.mp3')
		return str(resp)
	
	with resp.gather(numDigits=1, action='/secure_message/passauth/' + str(remind_id), method='POST') as g:
		g.play('/assets/audio/hello_importantmessage.mp3')
		g.play('/assets/audio/pressanynumtohearmessage.mp3')
	return str(resp)		

@app.route("/secure_message/passauth/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_passauth(remind_id):
	'''after we call the patient, ask for passcode'''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	try:
		# find the record in the DB that corresponds to this call
		record = Reminder.query.get(remind_id)
	except:
		resp.play('/assets/audio/messageretrievalfail.mp3')
		return str(resp)

	with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
		g.play('/assets/audio/pleaseenterpasscoderetrieve.mp3')
	return str(resp)

@app.route("/secure_message/playback/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_playback(remind_id):
	'''play the message for the patient'''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)

	# find the record in the DB that corresponds to this call
	record = Reminder.query.get(remind_id)
	
	if record.passcode != passcode:
		with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
			g.play('/assets/audio/passcodeincorrect.mp3')
		return str(resp)
	else:
		record.delivered = True
		db_session.add(record)
		db_session.commit()
		
		#deliver_callback.apply_async(args=[remind_id, record.from_phone])
		resp.play('/assets/audio/pleasewaittohearmessage.mp3')
		resp.play(record.message + "&key=" + twilio_server_key, mimetype="audio/mpeg")
		resp.play('/assets/audio/messagewillrepeat.mp3')
		resp.play(record.message + "&key=" + twilio_server_key, loop=5, mimetype="audio/mpeg")
		resp.play('/assets/audio/goodbye.mp3')
		return str(resp)

@app.route("/secure_message/delivered/<int:remind_id>", methods=["GET", "POST"])
def secure_message_delivered(remind_id):
	'''call the originial person who made secure message and tell them it was delivered'''

	if request.values.get('AccountSid', None) != twilio_AccountSID:
		return "Not Authorized", 403 	#requests must come from Twilio

	resp = twilio.twiml.Response()

	# find the record in the DB that corresponds to this call
	record = Reminder.query.get(remind_id)
	
	resp.play('/assets/audio/deliverpart1.mp3')
	resp.say(' '.join(record.to_phone))
	resp.play('/assets/audio/deliverpart2.mp3')
	return str(resp)


@app.route("/caller_id_dial", methods=['GET','POST'])
def caller_id_dial():
	''' dials out from the EHHOP phone number'''

	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)
	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18773724161')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.play('/assets/audio/tryagainpress1.mp3')
	return str(resp)
	
@app.route("/caller_id_redial/<number>", methods=['GET','POST'])
def caller_id_redial(number):
	'''redials a number dialed out by caller_id_dial - digits only dialed once'''

	resp = twilio.twiml.Response()
	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18773724161')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.play('/assets/audio/tryagainpress1.mp3')
	return str(resp)
