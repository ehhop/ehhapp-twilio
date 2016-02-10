#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.database import db_session, query_to_dict
from ehhapp_twilio.models import User, Reminder, Intent, Assignment
from ehhapp_twilio.forms import *

import flask.ext.login as flask_login
from oauth2client import client as gauthclient
from oauth2client import crypt
from ftplib import FTP_TLS
from flask import flash

#logins
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(user_id):
	return User.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
	return render_template('login.html', 
				vm_client_id = vm_client_id)

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
    return "Logged out. You can close this window now."

@app.route('/flashplayer', methods=['GET'])
def serve_vm_player():
	audio_url = request.values.get('a', None)
	return render_template("player_twilio.html",
				audio_url = audio_url, 
				vm_client_id = vm_client_id)

@app.route('/reminders', methods=['GET'])
@flask_login.login_required
def serve_vm_admin():
	reminders = query_to_dict(Reminder.query.all())
	return render_template("voicemails.html", 
				data = reminders)

@app.route('/reminders/<int:remind_id>/delete', methods=['GET'])
@flask_login.login_required
def delete_reminder(remind_id):
	record = Reminder.query.get(remind_id)
	if record == None:
		flash('Could not find reminder in database.')
		return redirect(url_for('serve_vm_admin'))
	else:
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_vm_admin'))				

@app.route('/assignments/delete<int:assign_id>', methods=['GET'])
@flask_login.login_required
def delete_assignment(assign_id):
	record = Assignment.query.get(assign_id)
	if record == None:
		flash('Could not find assignment in database.')
		return redirect(url_for('serve_assignment_admin'))
	else:
		flash('Assignment removed.')
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_assignment_admin'))				

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

@app.route('/intents', methods=['GET'])
@flask_login.login_required
def serve_intent_admin():
        intents = query_to_dict(Intent.query.all())
        return render_template("intents.html",
                                data = intents)

@app.route('/assignments', methods=['GET'])
@flask_login.login_required
def serve_assignment_admin():
        assignments = query_to_dict(Assignment.query.all())
        return render_template("assignments.html",
                                data = assignments)

@app.route('/intents/edit', methods=['GET', 'POST'])
@flask_login.login_required
def add_intent():
	form = IntentForm(request.form)
	if request.method == 'POST' and form.validate():
		intent = Intent(form.digit.data, form.description.data, form.required_recipients.data,
				form.distributed_recipients.data)
		db_session.add(intent)
		db_session.commit()
		flash('Intent added.')
		return redirect(url_for('serve_intent_admin'))
	return render_template("intent_form.html", action="Add", data_type="an intent", form=form)

@app.route('/intents/edit<int:intent_id>', methods=['GET', 'POST'])
@flask_login.login_required
def edit_intent(intent_id):
	intent = Intent.query.get(intent_id)
	formout = IntentForm(obj=intent)
	form = IntentForm(request.form)
	if request.method == 'POST' and form.validate():
		intent.digit = form.digit.data
		intent.description = form.description.data
		intent.required_recipients = form.required_recipients.data
		intent.distributed_recipients = form.distributed_recipients.data
		db_session.add(intent)
		db_session.commit()
		flash('Intent edited.')
		return redirect(url_for('serve_intent_admin'))
	return render_template("intent_form.html", action="Edit", data_type=intent.digit, form=formout)

@app.route('/assignments/edit', methods=['GET', 'POST'])
@flask_login.login_required
def add_assignment():
	form = AssignmentForm(request.form)
	if request.method == 'POST' and form.validate():
		assignment = Assignment(form.from_phone.data, form.recipients.data)
		db_session.add(assignment)
		db_session.commit()
		flash('Assignment added.')
		return redirect(url_for('serve_assignment_admin'))
	return render_template("intent_form.html", action="Add", data_type="an assignment", form=form)

@app.route('/assignments/edit<int:assign_id>', methods=['GET', 'POST'])
@flask_login.login_required
def edit_assignment(assign_id):
	assign = Assignment.query.get(assign_id)
	formout = AssignmentForm(obj=assign)
	form = AssignmentForm(request.form)
	if request.method == 'POST' and form.validate():
		assign.from_phone = form.from_phone.data
		assign.recipients = form.recipients.data
		db_session.add(assign)
		db_session.commit()
		flash('Assignment edited.')
		return redirect(url_for('serve_assignment_admin'))
	return render_template("intent_form.html", action="Edit", data_type=assign.from_phone, form=formout)

@app.route('/intents/test<int:intent_id>', methods=['GET', 'POST'])
@flask_login.login_required
def test_intent(intent_id):
	intent = Intent.query.get(intent_id)
	if intent == None:
		flash('ERROR: Intent not in DB.')
		return redirect(url_for('serve_intent_admin'))		
	db = EHHOPdb(credentials)
	requireds = intent.required_recipients.split(',')
	requireresult = dict()
	flash("Required recipients:")
	for r in requireds:
		pos = r.strip(" ")
		requireresult[pos] = db.lookup_name_by_position(pos)
		flash(pos + ": " + str(requireresult[pos]))
	assigns = intent.distributed_recipients.split(',')
	assignresult = dict()
	flash("Assign from these:")
	for a in assigns:
		pos = a.strip(" ")
		assignresult[pos] = []
		interresult = db.lookup_name_in_schedule(pos, getSatDate())
		for i in interresult:
			phone = db.lookup_phone_by_name(i)
			assignresult[pos].append([i, phone])
		flash(pos + ": " + str(assignresult[pos]))
	return redirect(url_for('serve_intent_admin'))

		

