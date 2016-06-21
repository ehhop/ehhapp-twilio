#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.backgroundtasks import *

@app.route("/handle_key/hello", methods=["GET", "POST"])
def handle_key_hello():
	'''respond to initial direction from the welcome greeting (1st menu)'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None) 				# get digit pressed
	day_of_week = datetime.now(pytz.timezone('US/Eastern')).weekday()	# get day of week (0 is Monday and 6 is Sunday)
	if digit == '1':						   	# pressed 1 - english
		'''instructions in english selected'''
		with resp.gather(numDigits=1, action="/new_established_menu", method="POST") as g:
			for i in range(0,3):
				g.play("/assets/audio/new_established_menu.mp3")
				g.pause(length=5)
	elif digit == '2':							# pressed 2 - spanish
		'''instructions in spanish selected'''
		with resp.gather(numDigits=1, action="/sp/new_established_menu", method="POST") as g:
			for i in range(0,3):
				g.play('/assets/audio/sp_new_established_menu.mp3')	# spanish: list options 1-7 similar to english
				g.pause(length=5)
	elif digit == "#": 							# dial extension feature
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('/assets/audio/pleasedial4digit.mp3')
	elif digit == '*':							# ehhop_members_path menu
		with resp.gather(numDigits=8, action='/auth_menu', method="POST") as g:
			g.play('/assets/audio/enterpasscode.mp3')
	else:	
		resp.play('/assets/audio/incorrectkey.mp3')			# They have pressed an incorrect key.
		resp.redirect('/')
	return str(resp)							# Return response

@app.route("/new_established_menu", methods=["GET","POST"])
def new_established_menu():
	'''respond to digit press when the clinic is open'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)				# get keypress
	if digit == "2":
		resp.redirect("/take_message/9")
	elif digit == "3":
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
                        for i in range(0,3):
                                g.play("/assets/audio/clinic_open_menu.mp3")
                                g.pause(length=5)
	else:
		resp.play('/assets/audio/incorrectkey.mp3')			# They have pressed an incorrect key.
		resp.redirect('/new_established_menu')
	return str(resp)		
	
@app.route("/handle_key/clinic_open_menu", methods=["GET", "POST"])
def clinic_open_menu():
	'''respond to digit press when the clinic is open'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)				# get keypress

	oncall_current_phone = getOnCallPhoneNum()				# get the phone # of the on call - fallback if something wrong

	if intent == '1':  							# urgent concern
		resp.play("/assets/audio/xfer_call.mp3")			# now transferring to oncall
		resp.dial(oncall_current_phone)					# dial current oncall TS
		resp.play('/assets/audio/allbusy_trylater.mp3')			# if call fails (not picked up)
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g: 	# replay open menu after failure
				g.play("/assets/audio/clinic_open_menu.mp3")
				g.pause(length=5)
	elif intent in [str(i.digit) for i in Intent.query.all() if int(i.digit) >= 2]:				# patient doesnt have appt today (everything else)
		return redirect('/take_message/' + intent)			# take a message
	else:									# accidental key press
		resp.play('/assets/audio/incorrectkey.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:	# replay open menu after accidential keypress
			g.play("/assets/audio/clinic_open_menu.mp3")
			g.pause(length=5)
	return str(resp)							# return response

@app.route("/handle_key/clinic_closed_menu", methods=["GET", "POST"])
def clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)				# get keypress
	
	if intent in [i.digit for i in models.Intent.query.all() if int(i.digit) >= 2]:					# patient doesnt have appointment today
		return redirect("/take_message/" + intent)			# take a message
	else:									# presed incorrect key
		resp.play('/assets/audio/incorrectkey.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g: 	#replay closed menu
			g.play("/assets/audio/clinic_closed_menu.mp3")
			g.pause(length=5)
	return str(resp)							# return response
	
@app.route("/take_message/<int:intent>", methods=['GET', 'POST'])
def take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	
	resp = twilio.twiml.Response()
	if intent == 0:								# used by dial_extension to send direct VM messages
		to_email = request.values.get('to_email', fallback_email)	# fallback to send email to IT
		after_record = '/handle_recording/' + str(intent) + '?to_email=' + to_email	# callback after VM left
	else:
		after_record = '/handle_recording/' + str(intent)		# callback after VM left
	
	if intent == 9:							# new patient options
		resp.play("/assets/audio/new_patient_options.mp3")
	else:									# non-urgent message
		# Please leave a message for us after the tone. Make sure to let us know what 
		# times we can call you back. We will call you back within one day.
		resp.play("/assets/audio/nonurgent_message.mp3")

	resp.play("/assets/audio/vm_instructions.mp3")				# additional instructions 
										### - merge this with ones above!
	resp.record(maxLength=300, action=after_record, method="POST")		# after patient leaves message, direct them to next step
	return str(resp)							# return response

@app.route("/handle_recording/<int:intent>", methods=['GET', 'POST'])
def handle_recording(intent):
	'''patient has finished leaving recording'''
	resp = twilio.twiml.Response()
	ani = request.values.get('From', 'None')				# get patient's caller id
	to_email = request.values.get('to_email', None)				# if a specific person needs this (dial_extension)
	no_requireds = True if to_email != None else False			# used by dial_extension to send direct VMs
	recording_url = request.values.get("RecordingUrl", None)		# get the recording URL from Twilio

	async_process_message.delay(recording_url, intent, ani, assign=to_email, no_requireds=no_requireds)	# process message asynchronously 
														# (e.g. download and send emails) using Celery
	###if the message was successfully sent... TODO to check
	resp.play("/assets/audio/sent_message.mp3")				# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	return str(resp)							# return response

@app.route("/dial_extension", methods=["GET", "POST"])
def dial_extension():
	'''searches for a student's extension 
	and takes a VM which gets emailed to them'''
	resp = twilio.twiml.Response()
	digits = request.values.get('Digits', None)				# get four digit extension
	database = EHHOPdb(credentials)						# open Google drive (database_helpers.py)
	try:									# try to get extension
		return_num = database.lookup_phone_by_extension(int(digits))
	except:									# if the app crashes/GDrive is down
		resp.play('/assets/audio/couldntfindext.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:	# ask to enter it again
			g.play('/assets/audio/pleasedial4digit.mp3')
		return str(resp)
	if return_num == None:							# if extension not found
		resp.play('/assets/audio/couldntfindext.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:	# ask to enter it again
			g.play('/assets/audio/pleasedial4digit.mp3')
	else:
		resp.say("Sending you to the mailbox of " + return_num[0], voice='alice', language='en-US')
		resp.pause(length=1)
		resp.redirect('/take_message/0?to_email=' + return_num[2])	# have them leave a message for the person (can also make this live dialing)
	return str(resp)							# return response

@app.route("/next_clinic/<person_type>/", methods=["GET", "POST"])
def find_in_schedule(person_type):
	'''find person in schedule for next clinic'''				#CURRENTLY NOT USED (why? I don't know - Ryan)
	resp = twilio.twiml.Response()
	database = EHHOPdb(credentials)
	return_num = None
	try:
		satdate = str(ehhapp_twilio.database_helpers.getSatDate())
		return_names = database.lookup_name_in_schedule(person_type, satdate)
		if return_names != []:
			return_num = database.lookup_phone_by_name(return_names[0])
	except:
		resp.play('/assets/audio/systemfailure.mp3')
		return str(resp)
		
	if return_num == None:
		resp.play('/assets/audio/couldntfindpersonindb.mp3')
	else:
		resp.say("Connecting you with " + return_names[0], voice='alice', language='en-US')
		resp.pause(length=3)
		resp.dial(return_num, callerId='+18622425952')
		resp.play('/assets/audio/callfailed-goodbye.mp3')
	return str(resp)

@app.route("/find_person/<person_type>/", methods=["GET", "POST"])
def find_person(person_type):							#find a person in the database - CURRENTLY NOT USED
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

# END
