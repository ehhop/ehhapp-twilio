from flask import Flask, request, redirect, send_from_directory, Response, stream_with_context, url_for, render_template
from requests.auth import HTTPBasicAuth
from ehhapp_twilio.config import *
import twilio.twiml
from twilio.rest import TwilioRestClient

#Flask init
app = Flask(__name__, static_folder='')
app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = flask_secret_key
app.debug = True

client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

from ehhapp_twilio.database import db_session
import ehhapp_twilio.backgroundtasks
import ehhapp_twilio.database_helpers
import ehhapp_twilio.voicemail_helpers
import ehhapp_twilio.email_helper
import ehhapp_twilio.english_path
import ehhapp_twilio.spanish_path
import ehhapp_twilio.ehhop_members_path
import ehhapp_twilio.welcome

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
