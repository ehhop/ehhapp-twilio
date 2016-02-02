#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *

@app.route('/', methods=['GET', 'POST'])
def hello_ehhop():
	'''respond to incoming requests:'''
	
	#Gracias por llamar a la Clinica de EHHOP. 
	#Para instrucciones en espanol, marque el numero 2. 
	#Thank you for calling the EHHOP clinic. 
	#If this is an emergency please 
	#hang up and dial 9 1 1 now.
	#For instructions in English, please press 1.
	#If you know your party's extension, please press 3.
	#EHHOP es la Asociacion Comunitaria para la Salud de 
	#East Harlem en Mount Sinai. Si esto es una emergencia, 
	#cuelgue el telefono y llame ahora al 9-1-1. We are the 
	#East Harlem Health Outreach Partnership of the Icahn School 
	#of Medicine at Mount Sinai. 

	# check if patient has a secure message waiting - if so redirect
	callerid = request.values.get('From', None)
	if callerid != None:
		callerid = callerid[-10:]
		db = open_db()	
		r = db['reminders']
		record = r.find_one(to_phone=callerid, delivered=False, order_by=['-id'])
		if record != None:
			return redirect(url_for('secure_message_callback', remind_id = record['id']))
	
	resp = twilio.twiml.Response()
	with resp.gather(numDigits=1, action="/handle_key/hello", method="POST") as g:
		for i in range(0,3):
			g.play("/assets/audio/welcome_greeting_ehhop.mp3")
			g.pause(length=5)
	return str(resp)
