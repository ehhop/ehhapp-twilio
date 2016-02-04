#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.database import db_session, query_to_dict
from ehhapp_twilio.models import User, Reminder

import flask.ext.login as flask_login
from oauth2client import client as gauthclient
from oauth2client import crypt
from ftplib import FTP_TLS
import sys
sys.path.append('/home/rneff/anaconda/lib/python2.7/site-packages')

#logins
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(user_id):
	return User.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
	return 'Not Authorized'

@app.route('/tokensignin', methods=['POST'])
def googleOAuthTokenVerify():
	#from https://developers.google.com/identity/sign-in/web/backend-auth
	token = request.values.get('idtoken', None)
	try:
		idinfo = gauthclient.verify_id_token(token, vm_client_id)
		# If multiple clients access the backend server:
		if idinfo['aud'] not in [vm_client_id]:
			raise crypt.AppIdentityError("Unrecognized client.")
		if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
			raise crypt.AppIdentityError("Wrong issuer.")
	except crypt.AppIdentityError:
		# Invalid token
		return None

	#okay, now we're logged in. yay!
	userid = idinfo['sub']
	useremail = idinfo['email']
	user = User.query.get(useremail)
	if user:
		user.authenticated=True
		db_session.add(user)
		db_session.commit()
		flask_login.login_user(user, remember=True)
	else:
		if '@icahn.mssm.edu' not in useremail:
			return 'Unauthorized e-mail address. You must be a ISMMS student with an @icahn.mssm.edu address!'
		else:
			user = User(email = useremail, google_token=userid)
			user.authenticated=True
			db_session.add(user)
			db_session.commit()
			flask_login.login_user(user, remember=False)
	return useremail

@app.route("/logout", methods=["GET", "POST"])
@flask_login.login_required
def logout():
    """Logout the current user."""
    user = flask_login.current_user
    user.authenticated = False
    db_session.add(user)
    db_session.commit()
    flask_login.logout_user()
    return "Logged out."

@app.route('/flashplayer', methods=['GET'])
def serve_vm_player():
	audio_url = request.values.get('a', None)
	return render_template("player_twilio.html",
				audio_url = audio_url, 
				vm_client_id = vm_client_id)

@app.route('/voicemails', methods=['GET'])
@flask_login.login_required
def serve_vm_admin():
	import pandas as pd
	reminders = pd.DataFrame(query_to_dict(Reminder.query.all()))
	return render_template("voicemails.html", 
							data = reminders.to_html(classes='table table-striped'))

@flask_login.login_required
@app.route('/play_recording', methods=['GET', 'POST'])
def play_vm_recording():
	twilio_client_key = request.values.get('key', None)
	if twilio_server_key != twilio_client_key:
		if not flask_login.current_user.is_authenticated:
			return app.login_manager.unauthorized()
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
		class VMFile:
  			def __init__(self):
    				self.data = ""
  			def __call__(self,s):
     				self.data += s
		v = VMFile()
		session = FTP_TLS('ftp.box.com', box_username, box_password)
		session.retrbinary('RETR recordings/' + filename, v)
		session.close()
		return v.data
	
	# serve file
	return Response(get_file(filename), mimetype='audio/wav')
