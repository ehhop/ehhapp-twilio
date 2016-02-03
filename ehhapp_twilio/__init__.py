from flask import Flask, request, redirect, send_from_directory, Response, stream_with_context, url_for, render_template
from requests.auth import HTTPBasicAuth
from ehhapp_twilio.config import *
import twilio.twiml
from twilio.rest import TwilioRestClient
client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)

#Flask init
app = Flask(__name__, static_folder='')
app.config['CELERY_BROKER_URL'] = 'redis://:' + redis_pass + '@localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://:' + redis_pass + '@localhost:6379/0'
app.config['CELERY_ENABLE_UTC'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = flask_secret_key
app.debug = True

client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

import ehhapp_twilio.backgroundtasks
import ehhapp_twilio.database_helpers
import ehhapp_twilio.voicemail_helpers
import ehhapp_twilio.email_helper
import ehhapp_twilio.english_path
import ehhapp_twilio.spanish_path
import ehhapp_twilio.ehhop_members_path
import ehhapp_twilio.welcome
