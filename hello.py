import os
import datetime, pytz
from flask import Flask, request, redirect
import twilio.twiml

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
		g.play("https://s3.amazonaws.com/ehhapp-phone/welcome_greeting_ehhop.mp3", loop=3)
		
	return str(resp)

@app.route("/handle_key/hello", methods=["GET", "POST"])
def handle_key_hello():
	'''respond to initial direction'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)
	
	if digit == '1':
		'''instructions in english selected'''
		
		#get day of week (0 is Monday and 6 is Sunday)
		day_of_week = datetime.datetime.now(pytz.timezone('US/Eastern')).weekday()
		
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
				g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3", loop=3)
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
				g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3", loop=3)
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
	
