import sys, os, pytz, re, ftplib
from datetime import datetime, timedelta
from SOAPpy import WSDL
from flask import Flask, request, redirect, send_from_directory, Response
import twilio.twiml

base_dir = os.path.dirname(os.path.realpath(__file__))
execfile(base_dir + "/gdatabase.py")
execfile(base_dir + "/email_helper.py")

wsdlfile='http://phone.ehhapp.org/services.php?wsdl'

app = Flask(__name__, static_folder='')

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
	with resp.gather(numDigits=1, action="/handle_key/hello", method="GET") as g:
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
			with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="GET") as g:
				
				#If you have an appointment today, please press 1. 
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				for i in range(0,3):
					g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
					g.pause(length=5)
		else:
			with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="GET") as g:
				
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
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="GET") as g:
				# spanish: list options 1-4 similar to english
				for i in range(0,3):
					g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
					g.pause(length=5)
		else: #clinic not open
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="GET") as g:
				# spanish: list options 2-4 similar to english
				for i in range(0,3):
					g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_closed_menu.mp3')
					g.pause(length=5)
	elif digit == "3": 
		'''extension feature'''
		with resp.gather(numDigits=4, action="/dial_extension", method="GET") as g:
			g.say("Please dial your four digit extension now.", voice='alice', language="en-US")
		
	elif digit == '*':
		'''caller id feature'''
		with resp.gather(numDigits=8, action='/caller_id_auth', method='GET') as g:
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
		with resp.gather(numDigits=4, action="/dial_extension", method="GET") as g:
			g.say("Please dial your four digit extension now.", voice='alice', language="en-US")
		return str(resp)
	if return_num == None:
		resp.say("I'm sorry, I couldn't find that extension.")
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="GET") as g:
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
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="GET") as g:
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
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="GET") as g:
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
		with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="GET") as g: 
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
	resp.record(maxLength=300, action=after_record)	

	return str(resp)

@app.route("/handle_recording/<int:intent>", methods=['GET', 'POST'])
def handle_recording(intent):
	'''patient has finished leaving recording'''
	resp = twilio.twiml.Response()
	ani = request.values.get('From', 'None')
	recording_url = request.values.get("RecordingUrl", None)

	# process message (e.g. download and send emails)
	process_recording(recording_url, intent, ani)

	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sent_message.mp3")
	return str(resp)

@app.route("/caller_id_auth", methods=['GET','POST'])
def caller_id_auth():
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)
	
	if passcode == '12345678':
		#success
		with resp.gather(numDigits=10, action='/caller_id_dial', method='GET') as g:
			g.say("Please enter the ten-digit phone number you wish to call, starting with the area code", voice='alice')
		return str(resp)
	else:
		resp.say("I'm sorry, that passcode is incorrect.", voice='alice')
		with resp.gather(numDigits=8, action='/caller_id_auth', method='GET') as g:
			g.say("Please enter your passcode.", voice='alice')
		return str(resp)

@app.route("/caller_id_dial", methods=['GET','POST'])
def caller_id_dial():
	''' dials out from the EHHOP phone number'''

	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)

	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='GET') as g:
		g.say("If you would like to try again, please press 1, otherwise, hang up now.", voice='alice', language='en-US')

	return str(resp)
	
@app.route("/caller_id_redial/<number>", methods=['GET','POST'])
def caller_id_redial(number):
	'''redials a number dialed out by caller_id_dial - digits only dialed once'''

	resp = twilio.twiml.Response()
	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='GET') as g:
		g.say("If you would like to try again, please press 1, otherwise, hang up now.", voice='alice', language='en-US')
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
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="GET") as g:
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
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="GET") as g:
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
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="GET") as g:
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
	resp.record(maxLength=300, action=after_record)
	
	return str(resp)

@app.route("/sp/handle_recording/<int:intent>", methods=['GET', 'POST'])
def sp_handle_recording(intent):
	'''patient has finished leaving recording'''
        resp = twilio.twiml.Response()
        ani = request.values.get('From', 'None')
        recording_url = request.values.get("RecordingUrl", None)

        # process message (e.g. download and send emails)
        process_recording(recording_url, intent, ani)
	
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
		session = ftplib.FTP('ftp.box.com', box_username, box_password)
		session.retrbinary('RETR recordings/' + filename, lambda chunk: (yield chunk))
		session.close()
	
	# serve file
	return Response(get_file(), mimetype='audio/wav')

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

#============MUST BE LAST LINE================
if __name__ == '__main__':
	app.debug = True
	app.run()

