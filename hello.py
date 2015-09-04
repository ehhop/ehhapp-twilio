import os
from flask import Flask
import twilio.twiml

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello_monkey():
	'''
	respond to incoming requests:
	
	Gracias por llamar a la Clínica de EHHOP. 
	Para instrucciones en español, marque el número 2. 
	Thank you for calling the EHHOP clinic. 
	For instructions in English, please press 1. 
	EHHOP es la Asociación Comunitaria para la Salud de 
	East Harlem en Mount Sinai. Si esto es una emergencia, 
	cuelgue el teléfono y llame ahora al 9-1-1. We are the 
	East Harlem Health Outreach Partnership of the Icahn School 
	of Medicine at Mount Sinai. If this is an emergency please 
	hang up and dial 9 1 1 now.
	'''
	

	resp = twilio.twiml.Response()
	resp.play("recordings/welcome_greeting.mp3")

	return str(resp)
