from flask import Flask, request, redirect, send_from_directory, Response, stream_with_context, url_for, render_template
from requests.auth import HTTPBasicAuth
from ehhapp_twilio.config import *
import twilio.twiml
from twilio.rest import TwilioRestClient
from flask.ext.mail import Mail

#Flask init
app = Flask(__name__, static_folder='')
app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = flask_secret_key
app.debug = True # THIS LOGS TO system when in debug, email in production (False)

mail = Mail(app)

client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
auth_combo=(twilio_AccountSID, twilio_AuthToken)

from ehhapp_twilio.database import db_session 	# to make sqlalchemy calls
import ehhapp_twilio.backgroundtasks		# celery specific stuff
import ehhapp_twilio.database_helpers		# google drive functions (EHHOPdb)
import ehhapp_twilio.voicemail_helpers		# GUI for the voicemail system, logins, playing VMs
import ehhapp_twilio.email_helper		# sending emails, processing reoordings 
						#	after someone leaves a message
import ehhapp_twilio.english_path		# Twilio path for english
import ehhapp_twilio.spanish_path		# Twilio path for spanish
import ehhapp_twilio.ehhop_members_path		# Twilio path when you press the '*' key after you call
import ehhapp_twilio.welcome			# initial greeting

import logging
from logging.handlers import SMTPHandler
mail_handler = SMTPHandler('localhost',
                               'server-error@twilio.ehhapp.org',
                              	'ryan.neff@icahn.mssm.edu', 'EHHAPP-Twilio Failed')
mail_handler.setLevel(logging.WARNING)
app.logger.addHandler(mail_handler)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
