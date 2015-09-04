import os
from flask import Flask, request, send_from_directory
import twilio.twiml

app = Flask(__name__, static_folder='/home/neffra/test_twilio/recordings')

@app.route('/', methods=['GET', 'POST'])
def hello_monkey():
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
	resp.play("https://s3.amazonaws.com/ehhapp-phone/welcome_greeting_ehhop.mp3")

	return str(resp)
