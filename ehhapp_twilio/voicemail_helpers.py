#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *

import flask.ext.login as flask_login
from flask_sqlalchemy import SQLAlchemy
from oauth2client import client as gauthclient
from oauth2client import crypt
from ftplib import FTP_TLS

#logins
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

#SQLAlchemy
db2 = SQLAlchemy(app)

class User(db2.Model):
    """An admin user capable of viewing reports.

    :param str email: email address of user
    :param str google_token: callback token

    """
    __tablename__ = 'user'

    email = db2.Column(db2.String, primary_key=True)
    google_token = db2.Column(db2.String)
    authenticated = db2.Column(db2.Boolean, default=False)

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.email

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False
    
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
		db2.session.add(user)
		db2.session.commit()
		flask_login.login_user(user, remember=True)
	else:
		if '@icahn.mssm.edu' not in useremail:
			return 'Unauthorized e-mail address. You must be a ISMMS student with an @icahn.mssm.edu address!'
		else:
			user = User(email = useremail, google_token=userid)
			user.authenticated=True
			db2.session.add(user)
			db2.session.commit()
			flask_login.login_user(user, remember=False)
	return useremail

@app.route("/logout", methods=["GET", "POST"])
@flask_login.login_required
def logout():
    """Logout the current user."""
    user = flask_login.current_user
    user.authenticated = False
    db2.session.add(user)
    db2.session.commit()
    flask_login.logout_user()
    return "Logged out."

@app.route('/flashplayer', methods=['GET'])
def serve_vm_player():
	audio_url = request.values.get('a', None)
	return render_template("player_twilio.html",
				audio_url = audio_url, 
				vm_client_id = vm_client_id)

@flask_login.login_required
@app.route('/play_recording', methods=['GET', 'POST'])
def play_vm_recording():
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
		chunks = []
		session = FTP_TLS('ftp.box.com', box_username, box_password)
		session.retrbinary('RETR recordings/' + filename, chunks.append)
		session.close()
		for chunk in chunks:
			yield chunk
	
	# serve file
	return Response(get_file(filename), mimetype='audio/wav')
