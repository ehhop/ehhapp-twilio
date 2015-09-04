import os, pytz, re
from datetime import datetime, timedelta
from SOAPpy import WSDL
from flask import Flask, request, redirect
import twilio.twiml

wsdlfile='http://phone.ehhapp.org/services.php?wsdl'

app = Flask(__name__, static_folder='')

@app.route('/', methods=['GET', 'POST'])
def hello_ehhop():
	'''respond to incoming requests:'''
	
	#Gracias por llamar a la Clinica de EHHOP. 
	#Para instrucciones en espanol, marque el numero 2. 
	#Thank you for calling the EHHOP clinic. 
	#For instructions in English, please press 1. 
	#EHHOP es la Asociacion Comunitaria para la Salud de 
	#East Harlem en Mount Sinai. Si esto es una emergencia, 
	#cuelgue el telefono y llame ahora al 9-1-1. We are the 
	#East Harlem Health Outreach Partnership of the Icahn School 
	#of Medicine at Mount Sinai. If this is an emergency please 
	#hang up and dial 9 1 1 now.

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
	
	if digit == '1':
		'''instructions in english selected'''
		
		#get day of week (0 is Monday and 6 is Sunday)
		day_of_week = datetime.now(pytz.timezone('US/Eastern')).weekday()
		
		if day_of_week == 5: #clinic is open on Saturdays
			with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="GET") as g:
				# The EHHOP clinic phone number has been changed to 877-372-4161.  
				# Please save this number, because the old one will soon be discontinued. 
				# Again, the new EHHOP number is 877-372-4161.
				g.play('https://s3.amazonaws.com/ehhapp-phone/ehhop_phone_changed.mp3')
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
				# The EHHOP clinic phone number has been changed to 877-372-4161.  
				# Please save this number, because the old one will soon be discontinued. 
				# Again, the new EHHOP number is 877-372-4161.
				g.play('https://s3.amazonaws.com/ehhapp-phone/ehhop_phone_changed.mp3')
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				for i in range(0,3):
					g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3")
					g.pause(length=5)
	elif digit == '2':
		'''instructions in spanish selected'''
		#TODO
		resp.say("This feature is currently under construction. Goodbye!", voice='alice', language='en-US')
	elif digit == '*':
		'''caller id feature'''
		#todo
		resp.say("This feature is currently under construction. Goodbye!", voice='alice', language='en-US')
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
	
	# get next saturday's date
	time_now = datetime.now(pytz.timezone('US/Eastern'))
	day_of_week = time_now.weekday()
	addtime = None
	if day_of_week == 6:
		addtime=timedelta(6)
	else:
		addtime=timedelta(5-day_of_week)
	satdate = (time_now+addtime).strftime('%Y-%m-%d')
	
	# get the phone # of the on call
	server = WSDL.Proxy(wsdlfile)
	oncall_phone_unsan = server.get_oncall_CM_phone(nearest_saturday=satdate).strip('-')
	d = re.compile(r'[^\d]+')
	oncall_current_phone = '+1' + d.sub('', oncall_phone_unsan)
	
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
			#If you have an appointment today, please press 1. 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about medications, appointments, 
			#or other matters, please press 4.
			g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3")
			g.pause(length=5)
	
@app.route("/take_message/<intent>", methods=['GET', 'POST'])
def take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	# variables we need to set:
	# satdate - next saturday's date as yyyy-MM-dd
	# caller id - the number the call is coming from
	
	resp = twilio.twiml.Response()
	
	# get next saturday's date
	time_now = datetime.now(pytz.timezone('US/Eastern'))
	day_of_week = time_now.weekday()
	addtime = None
	if day_of_week == 6:
		addtime=timedelta(6)
	else:
		addtime=timedelta(5-day_of_week)
	
	satdate = (time_now+addtime).strftime('%Y-%m-%d')
	caller_id = request.values.get('From', 'None')
	
	after_record = '/handle_recording/' + intent + '/' + caller_id + '/' + satdate	
	
	if intent == '3':
		#Please leave a message for us after the tone. We will call you back as soon as possible.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/urgent_message.mp3")
	if intent in ['2','4']:
		#Please leave a message for us after the tone. We will call you back within one day.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/nonurgent_message.mp3")
	resp.play("https://s3.amazonaws.com/ehhapp-phone/vm_instructions.mp3")
	resp.record(maxLength=300, action=after_record, transcribe='true')
	
	return str(resp)

@app.route("/handle_recording/<int:intent>/<ani>/<satdate>", methods=['GET', 'POST'])
def handle_recording(intent, ani, satdate):
	'''patient has finished leaving recording'''
	
	resp = twilio.twiml.Response()
	recording_url = request.values.get("RecordingUrl", None)
	# send the notification to the server
	
	# get the phone # of the on call
	server = WSDL.Proxy(wsdlfile)
	vm_alert = server.voicemail_alert(intention=intent, ani=ani, nearest_saturday=satdate, recording_url=recording_url)
	
	# if the message was successfully sent...
	# ...no way to check? TODO
	resp.play("https://s3.amazonaws.com/ehhapp-phone/vm_instructions.mp3")
	return str(resp)
