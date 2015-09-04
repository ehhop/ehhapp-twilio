import os
from flask import Flask
import twilio.twiml

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello_monkey():
	'''respond to incoming requests'''

	welcome_greeting = "Thank you for calling the e hop clinic." + \
	"If this is a medical emergency please hang up and dial 9 1 1." + \
	"For instructions in English, please press 1." + \
	"We are the East Harlem Health Outreach Partnership of the Icahn " + \
	"School of Medicine at Mount Sinai. "

	resp = twilio.twiml.Response()
	resp.say(welcome_greeting, voice="woman", language="en", loop=3)

	return str(resp)
