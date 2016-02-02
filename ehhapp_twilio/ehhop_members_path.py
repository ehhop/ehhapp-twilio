#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *

import dataset

def open_db():
	db = dataset.connect(dataset_db)
	return db
	
@app.route("/auth_menu", methods=['GET','POST'])
def auth_menu():
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)
	
	if passcode == '12345678':
		#success
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			#To call Pacific Interpreters, please press 1.
			#To dial a patient using the ehhop number, please press 2.
			#To leave a secure message for a patient, please press 3. 			
			g.play('https://s3.amazonaws.com/ehhapp-phone/dial-vmremindermenu.mp3')
		return str(resp)
	else:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/incorrectkey.mp3')
		with resp.gather(numDigits=8, action='/auth_menu', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/enterpasscode.mp3')
		return str(resp)

@app.route("/auth_selection", methods=['GET','POST'])
def auth_selection():
	resp = twilio.twiml.Response()
	digit = request.values.get("Digits", None)
	
	if digit == '1':
		resp.dial('+18002641552', callerId='+18622425952')
		return str(resp)
	elif digit == '2':
		with resp.gather(numDigits=10, action='/caller_id_dial', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/entertodigits.mp3')
		return str(resp)
	elif digit == '3':
		with resp.gather(numDigits=10, action='/secure_message/setnum/', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/entertendigits-vm.mp3')
		return str(resp)
	else:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/incorrectkey.mp3')
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/dial-vmremindermenu.mp3')
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
			delivered=False,
			freq=24,
			message=None,
			name=None,
			passcode=None,
			spanish=None))
	
	with resp.gather(numDigits=6, action='/secure_message/setpass/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/youdialed.mp3')
		g.say(' '.join(number) + '. ', voice='alice')
		g.play('https://s3.amazonaws.com/ehhapp-phone/setpass.mp3')
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
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)

	# set a passcode and update the DB
	record['passcode'] = passcode
	r.update(record, ['id'])

	# ask for a reminder time
	with resp.gather(numDigits=1, action='/secure_message/settime/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/youdialed.mp3')
		g.say(' '.join(passcode) + ".", voice="alice")
		g.play('https://s3.amazonaws.com/ehhapp-phone/settime.mp3')
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
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
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
	resp.play('https://s3.amazonaws.com/ehhapp-phone/leavesecuremessage.mp3')
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
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)

	# set a new save file name randomly
	save_name = randomword(128) + ".wav"
	# set the secure recording URL location
	new_recording_url = 'https://twilio.ehhapp.org/play_recording?filename=' + save_name
	# set the message url and update the db
	record['message'] = new_recording_url
        r.update(record, ['id'])

	# download and save the message (async)
	save_secure_message.apply_async(args=[recording_url, save_name])

	with resp.gather(numDigits=1, action='/secure_message/send/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/confirmsecuremessage.mp3')
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
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)
	
	# we should have everything now, so make a record in celery for a call out
	set_async_message_deliver(record, remind_id)
	
	resp.play('https://s3.amazonaws.com/ehhapp-phone/securemessagesent.mp3')
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
		resp.play('https://s3.amazonaws.com/ehhapp-phone/hello_importantmessage.mp3')
		resp.play('https://s3.amazonaws.com/ehhapp-phone/messageretrievalfail.mp3')
		return str(resp)
	
	with resp.gather(numDigits=1, action='/secure_message/passauth/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/hello_importantmessage.mp3')
		g.play('https://s3.amazonaws.com/ehhapp-phone/pressanynumtohearmessage.mp3')
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
		resp.play('https://s3.amazonaws.com/ehhapp-phone/messageretrievalfail.mp3')
		return str(resp)

	with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/pleaseenterpasscoderetrieve.mp3')
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
			g.play('https://s3.amazonaws.com/ehhapp-phone/passcodeincorrect.mp3')
		return str(resp)
	else:
		record['delivered'] = True
		r.update(record, ['id'])
		deliver_callback.apply_async(args=[remind_id, record['from_phone']])
		resp.play('https://s3.amazonaws.com/ehhapp-phone/pleasewaittohearmessage.mp3')
		resp.play(record['message'])
		resp.play('https://s3.amazonaws.com/ehhapp-phone/messagewillrepeat.mp3')
		resp.play(record['message'], loop=5)
		resp.play('https://s3.amazonaws.com/ehhapp-phone/goodbye.mp3')
		return str(resp)

@app.route("/secure_message/delivered/<int:remind_id>", methods=["GET", "POST"])
def secure_message_delivered(remind_id):
	resp = twilio.twiml.Response()

	db = open_db()
	r = db['reminders']
	# find the record in the DB that corresponds to this call
	record = r.find_one(id=remind_id)
	
	resp.play('https://s3.amazonaws.com/ehhapp-phone/deliverpart1.mp3')
	resp.say(' '.join(record["to_phone"]))
	resp.play('https://s3.amazonaws.com/ehhapp-phone/deliverpart2.mp3')
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
		g.play('https://s3.amazonaws.com/ehhapp-phone/tryagainpress1.mp3')
	return str(resp)
	
@app.route("/caller_id_redial/<number>", methods=['GET','POST'])
def caller_id_redial(number):
	'''redials a number dialed out by caller_id_dial - digits only dialed once'''

	resp = twilio.twiml.Response()
	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/tryagainpress1.mp3')
	return str(resp)
