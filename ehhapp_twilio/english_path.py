#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.backgroundtasks import *

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
				#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
				#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
				#If you are an EHHOP patient and have a question about a bill you received, please press 6.
				#For all other non-urgent concerns, please press 7.
				#To hear this menu again, stay on the line.
				for i in range(0,3):
					g.play("/assets/audio/clinic_open_menu.mp3")
					g.pause(length=5)
		else:
			with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g:
				
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
				#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
				#If you are an EHHOP patient and have a question about a bill you received, please press 6.
				#For all other non-urgent concerns, please press 7.
				#To hear this menu again, stay on the line.
				for i in range(0,3):
					g.play("/assets/audio/clinic_closed_menu.mp3")
					g.pause(length=5)
					
	elif digit == '2':
		'''instructions in spanish selected'''
		# spanish: if this is an emerg, dial 911
		resp.play('/assets/audio/sp_emerg_911.mp3')
		if day_of_week == 5: #clinic is open on Saturdays
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
				# spanish: list options 1-4 similar to english
				for i in range(0,3):
					g.play('/assets/audio/sp_clinic_open_menu.mp3')
					g.pause(length=5)
		else: #clinic not open
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g:
				# spanish: list options 2-4 similar to english
				for i in range(0,3):
					g.play('/assets/audio/sp_clinic_closed_menu.mp3')
					g.pause(length=5)
	elif digit == "3": 
		'''extension feature'''
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('/assets/audio/pleasedial4digit.mp3')
		
	elif digit == '*':
		'''auth menu'''
		with resp.gather(numDigits=8, action='/auth_menu', method="POST") as g:
			g.play('/assets/audio/enterpasscode.mp3')
	
	else:
		'''They have pressed an incorrect key.'''
		return redirect('/')
	
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
		resp.play("/assets/audio/xfer_call.mp3")
		# dial current CM
		resp.dial(oncall_current_phone)
		# if the call fails
		resp.play('/assets/audio/allbusy_trylater.mp3')
		# replay initial menu
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
				#If you have an appointment today, please press 1. 
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				g.play("/assets/audio/clinic_open_menu.mp3")
				g.pause(length=5)
	# not been here before
	elif digit in ['2', '3', '4','5','6','7']:
		return redirect('/take_message/' + digit)
	# accidential key press
	else:
		resp.play('/assets/audio/incorrectkey.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
			#If you have an appointment today, please press 1. 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
			#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
			#If you are an EHHOP patient and have a question about a bill you received, please press 6.
			#For all other non-urgent concerns, please press 7.
			#To hear this menu again, stay on the line.
			g.play("/assets/audio/clinic_open_menu.mp3")
			g.pause(length=5)
	return str(resp)

@app.route("/handle_key/clinic_closed_menu", methods=["GET", "POST"])
def clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)
	
	if intent in ['2','3','4','5','6','7']:
		return redirect("/take_message/" + intent)
	else:
		resp.play('/assets/audio/incorrectkey.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g: 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
			#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
			#If you are an EHHOP patient and have a question about a bill you received, please press 6.
			#For all other non-urgent concerns, please press 7.
			#To hear this menu again, stay on the line.
			g.play("/assets/audio/clinic_closed_menu.mp3")
			g.pause(length=5)
	return str(resp)
	
@app.route("/take_message/<int:intent>", methods=['GET', 'POST'])
def take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	
	resp = twilio.twiml.Response()
	if intent == 0:
		to_email = request.values.get('to_email', fallback_email)
		after_record = '/handle_recording/' + str(intent) + '?to_email=' + to_email
	else:
		after_record = '/handle_recording/' + str(intent)
	
	if intent == '3':
		#Please leave a message for us after the tone. Make sure to let us know what times we can call you back. We will call you back as soon as possible.
		resp.play("/assets/audio/urgent_message.mp3")
	else:
		#Please leave a message for us after the tone. Make sure to let us know what times we can call you back. We will call you back within one day.
		resp.play("/assets/audio/nonurgent_message.mp3")

	#resp.play("/assets/audio/vm_instructions.mp3")

	# after patient leaves message, direct them to next step
	
	resp.record(maxLength=300, action=after_record, method="POST")

	return str(resp)

@app.route("/handle_recording/<int:intent>", methods=['GET', 'POST'])
def handle_recording(intent):
	'''patient has finished leaving recording'''
	resp = twilio.twiml.Response()
	ani = request.values.get('From', 'None')
	to_email = None
	positions = None
	if intent == 0:
		to_email = request.values.get('to_email', None)
	else:
		positions = ','.join(intentions[intent][1])
	recording_url = request.values.get("RecordingUrl", None)

	# process message asynchronously (e.g. download and send emails) using Celery
	async_process_message.delay(recording_url, intent, ani, positions, to_emails=to_email)

	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("/assets/audio/sent_message.mp3")
	return str(resp)

@app.route("/dial_extension", methods=["GET", "POST"])
def dial_extension():
	resp = twilio.twiml.Response()
	digits = request.values.get('Digits', None)
	database = EHHOPdb(credentials)
	try:
		return_num = database.lookup_phone_by_extension(int(digits))
	except:
		resp.play('/assets/audio/couldntfindext.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('/assets/audio/pleasedial4digit.mp3')
		return str(resp)
	if return_num == None:
		resp.play('/assets/audio/couldntfindext.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('/assets/audio/pleasedial4digit.mp3')
	else:
		resp.say("Sending you to the mailbox of " + return_num[0], voice='alice', language='en-US')
		resp.pause(length=1)
		resp.redirect('/take_message/0?to_email=' + return_num[2])
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
		resp.play('/assets/audio/systemfailure.mp3')
		return str(resp)
		
	if return_names == []:
		resp.play('/assets/audio/couldntfindpersonindb.mp3')
	else:
		for name in return_names:
			return_num = database.lookup_phone_by_name(name)
			if return_num != None:
				resp.say("Connecting you with " + name, voice='alice', language='en-US')
				resp.pause(length=3)
				resp.dial(return_num, callerId='+18622425952')
		resp.play('/assets/audio/callfailed-goodbye.mp3')
	return str(resp)

@app.route("/find_person/<person_type>/", methods=["GET", "POST"])
def find_person(person_type):
        resp = twilio.twiml.Response()
        database = EHHOPdb(credentials)
        return_num = None
        try:
                return_nums = database.lookup_name_by_position(person_type)      
        except:
                resp.play('/assets/audio/systemfailure.mp3')
                return str(resp)

        if return_num == []:
                resp.play('/assets/audio/couldntfindpersonindb.mp3')
        else:
                for return_num in return_nums:
                        if return_num != None:
                                resp.say("Connecting you with " + return_num[0], voice='alice', language='en-US')
                                resp.pause(length=3)
                                resp.dial(return_num[1], callerId='+18622425952')
                resp.play('/assets/audio/callfailed-goodbye.mp3')
        return str(resp)
