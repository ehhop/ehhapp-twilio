#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.backgroundtasks import *

@app.route("/sp/new_established_menu", methods=["GET","POST"])
def sp_new_established_menu():
	'''respond to digit press when the clinic is open'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)                              # get keypress
	day_of_week = datetime.now(pytz.timezone('US/Eastern')).weekday()       # get day of week (0 is Monday and 6 is Sunday)
	hour_of_day = datetime.now(pytz.timezone('US/Eastern')).hour
	#day_of_week = 5
        #hour_of_day = 9
        if digit == "2":
	        resp.redirect("/sp/take_message/9")
	elif digit == "3":
	    if (day_of_week == 5) & ((hour_of_day >=7) & (hour_of_day < 15)):
	        with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
	                for i in range(0,3):
	                        g.play("/assets/audio/sp_clinic_open_menu.mp3")
	                        g.pause(length=5)
	    else:
	        with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g:
	            for i in range(0,3):
	                        g.play("/assets/audio/sp_clinic_closed_menu.mp3")
	                        g.pause(length=5)
	else:
	        resp.redirect('/sp/new_established_menu')
	return str(resp)
	
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
	if (digit == '1') | (digit == '2'):
		# now transferring your call
		resp.play("/assets/audio/sp_xfer_call.mp3") # RE-RECORD
		# dial current CMs
		with resp.dial(timeout=15) as d:
			for number in oncall_current_phone:
				d.number(number)
		# if the call fails
		resp.play('/assets/audio/allbusy_trylater_sp.mp3') # RE-RECORD
		# replay initial menu
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
				g.play("/assets/audio/sp_clinic_open_menu.mp3")
				g.pause(length=5)
	# not been here before
	elif digit in [str(i.digit) for i in models.Intent.query.all() if int(i.digit) >= 0]:
		return redirect('/sp/take_message/' + digit)
	# accidential key press
	else:
		resp.play('/assets/audio/sp_incorrectkey.mp3') # RE-RECORD
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
			g.play("/assets/audio/sp_clinic_open_menu.mp3") # RE-RECORD
			g.pause(length=5)
	return str(resp)

@app.route("/handle_key/sp/clinic_closed_menu", methods=["GET", "POST"])
def sp_clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)
	
	if intent in [str(i.digit) for i in models.Intent.query.all() if int(i.digit) >= 0]:
		return redirect("/sp/take_message/" + intent)
	else:
		resp.play('/assets/audio/sp_incorrectkey.mp3') # RE-RECORD
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g: 
			g.play("/assets/audio/sp_clinic_closed_menu.mp3") # RE-RECORD
			g.pause(length=5)
	return str(resp)
	
@app.route("/sp/take_message/<int:intent>", methods=['GET', 'POST'])
def sp_take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	resp = twilio.twiml.Response()
	
	resp.play("/assets/audio/sp_vm_instructions.mp3")
	
	if intent == 0:
		to_email = request.values.get('to_email', fallback_email)
		after_record = '/sp/handle_recording/' + str(intent) + '?to_email=' + to_email
	else:
		after_record = '/sp/handle_recording/' + str(intent)
		
	if intent == 9:
		#Please leave a message for us after the tone. Make sure to let us know what times we can call you back. We will call you back as soon as possible.
		resp.play("/assets/audio/sp_new_patient_options.mp3")
	else:
		#Please leave a message for us after the tone. Make sure to let us know what times we can call you back. We will call you back within one day.
		resp.play("/assets/audio/sp_nonurgent_message.mp3")

	# after patient leaves message, direct them to next step	
	resp.record(maxLength=300, action=after_record, method="POST")
	return str(resp)

@app.route("/sp/handle_recording/<int:intent>", methods=['GET', 'POST'])
def sp_handle_recording(intent):
	'''patient has finished leaving recording'''
	resp = twilio.twiml.Response()
	ani = request.values.get('From', 'None')
	caller_id = request.values.get("CallerName", None)
	to_email = request.values.get('to_email', None)
	no_requireds = True if to_email != None else False
	recording_url = request.values.get("RecordingUrl", None)

	# process message asynchronously (e.g. download and send emails) using Celery
	async_process_message.delay(recording_url, intent, ani, assign=to_email, no_requireds=no_requireds, caller_id=caller_id)

	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("/assets/audio/sp_sent_message.mp3") # RE-RECORD
	return str(resp)

@app.route("/sp/dial_extension", methods=["GET", "POST"])
def sp_dial_extension():
	resp = twilio.twiml.Response()
	digits = request.values.get('Digits', None)
	database = EHHOPdb(credentials)
	try:
		return_num = database.lookup_phone_by_extension(int(digits))
	except:
		resp.play('/assets/audio/couldntfindext_sp.mp3') # RE-RECORD
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/sp/dial_extension", method="POST") as g:
			g.play('/assets/audio/pleasedial4digit_sp.mp3') # RE-RECORD
		return str(resp)
	if return_num == None:
		resp.play('/assets/audio/couldntfindext_sp.mp3') # RE-RECORD
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/sp/dial_extension", method="POST") as g:
			g.play('/assets/audio/pleasedial4digit_sp.mp3') # RE-RECORD
	else:
		resp.say("Que el envio al buzon de " + return_num[0], voice='alice', language='es') # translate this better
		resp.pause(length=1)
		resp.redirect('/sp/take_message/0?to_email=' + return_num[2])
	return str(resp)

@app.route("/sp/next_clinic/<person_type>/", methods=["GET", "POST"])
def sp_find_in_schedule(person_type):
	resp = twilio.twiml.Response()
	database = EHHOPdb(credentials)
	return_num = None
	try:
		satdate = str(ehhapp_twilio.database_helpers.getlastSatDate())
		return_names = database.lookup_name_in_schedule(person_type, satdate)
		if return_names != []:
			return_num = database.lookup_phone_by_name(return_names[0])
	except:
		resp.play('/assets/audio/systemfailure_sp.mp3') # RE-RECORD
		return str(resp)
		
	if return_num == None:
		resp.play('/assets/audio/couldntfindext_sp.mp3') # RE-RECORD
	else:
		resp.say("Que conecta con " + return_names[0], voice='alice', language='es')
		resp.pause(length=3)
		resp.dial(return_num, callerId='+18622425952')
		resp.play('/assets/audio/callfailed_sp.mp3') # RE-RECORD
		resp.play('/assets/audio/goodbye_sp.mp3')
	return str(resp)

@app.route("/sp/find_person/<person_type>/", methods=["GET", "POST"])
def sp_find_person(person_type):
        resp = twilio.twiml.Response()
        database = EHHOPdb(credentials)
        return_num = None
        try:
                return_nums = database.lookup_name_by_position(person_type)      
        except:
                resp.play('/assets/audio/systemfailure_sp.mp3') # RE-RECORD
                return str(resp)

        if return_num == []:
                resp.play('/assets/audio/couldntfindext_sp.mp3')
        else:
                for return_num in return_nums:
                        if return_num != None:
                                resp.say("Que conecta con " + return_num[0], voice='alice', language='es')
                                resp.pause(length=3)
                                resp.dial(return_num[1], callerId='+18622425952')
                resp.play('/assets/audio/callfailed_sp.mp3') # RE-RECORD
                resp.play('/assets/audio/goodbye_sp.mp3')
        return str(resp)
