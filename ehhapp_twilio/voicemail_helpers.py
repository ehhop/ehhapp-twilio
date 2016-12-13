#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *
from ehhapp_twilio.database import db_session
from ehhapp_twilio.models import *
from ehhapp_twilio.forms import *

import flask.ext.login as flask_login
from oauth2client import client as gauthclient
from oauth2client import crypt
from ftplib import FTP_TLS
from flask import flash

import pytz, os, shutil, random, string, sys
from datetime import datetime, timedelta

from sqlalchemy import desc

############# logins ############

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(user_id):				# used by Flask internally to load logged-in user from session
	return User.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():					# not logged-in callback
	return render_template('login.html', 
				vm_client_id = vm_client_id)

@app.route('/tokensignin', methods=['POST'])
def googleOAuthTokenVerify():				# authenticate with Google for Icahn accounts
	'''from https://developers.google.com/identity/sign-in/web/backend-auth'''
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
		sys.stderr.write("Bad token from client.\n")
		return None
							# okay, now we're logged in. yay!
	userid = idinfo['sub']
	useremail = idinfo['email']
	sys.stderr.write("Token sign in user: " + ", ".join([useremail, userid]) + "\n")
	user = User.query.get(useremail)
	if user:					# if user has been here before
		user.authenticated=True			# log them in in DB
		db_session.add(user)
		db_session.commit()
		flask_login.login_user(user, remember=True)	# log them in in their browser
	else:
		if ('@icahn.mssm.edu' not in useremail) & ('@mssm.edu' not in useremail):	# not ISMMS account
			return 'Unauthorized e-mail address. You must be a MSSM affiliate with an @icahn.mssm.edu or @mssm.edu address!'
		else:
			user = User(email = useremail, google_token=userid)	# create new user in DB
			user.authenticated=True		# log them in in DB
			db_session.add(user)
			db_session.commit()
			flask_login.login_user(user, remember=False)	# log them in in their browser
	return useremail				# return logged in email to user

@app.route("/logout", methods=["GET", "POST"])
@flask_login.login_required
def logout():
    """Logout the current user."""
    user = flask_login.current_user
    user.authenticated = False				# log out in db
    db_session.add(user)
    db_session.commit()
    flask_login.logout_user()				# delete browser cookie
    return "Logged out. You can close this window now."

######### PLAY VMs ##########

@app.route('/flashplayer', methods=['GET'])
def serve_vm_player():
	'''serves the play a voicemail page for a single voicemail'''
	audio_url = request.values.get('a', None)
	message_id = audio_url.split("=")[-1]
	vm_info = Voicemail.query.filter_by(message=message_id).first()
	vm_info.intent = Intent.query.filter_by(digit=vm_info.intent).first().description
	return render_template("player_twilio.html",
				audio_url = audio_url, 
				vm_client_id = vm_client_id, 
				vm_info = vm_info)


@app.route('/play_recording', methods=['GET', 'POST'])
def play_vm_recording():
	'''serve the voicemail or secure message for playback'''
	twilio_client_key = request.values.get('key', None)		# used when playing back messages over phone
	if twilio_server_key != twilio_client_key:
		if not flask_login.current_user.is_authenticated:	# if accessing VM through GUI
			return app.login_manager.unauthorized()

	''' plays a voicemail recording from the Box server'''
	filename = request.values.get('filename', None)
	# check that filename attribute was set, else return None
	if filename == None:
		return "Need to specify a filename.", 400

	# sterilize filename to prevent attacks
	safe_char = re.compile(r'[^\w.]+') # only alphanumeric and periods
	filename = safe_char.sub('', filename)

	def get_file(filename):						# how do we 'stream' the file from Box to browser? using a callback!
		class VMFile:						# this will store the VM message as a 
  			def __init__(self):				# memory object instead of in a file (+ deleted after execution)
    				self.data = ""
  			def __call__(self,s):
     				self.data += s
		v = VMFile()
		session = FTP_TLS('ftp.box.com', box_username, box_password)	# open Box
		session.retrbinary('RETR recordings/' + filename, v)	# add each chunk of data to memory from Box
		session.close()						# close Box
		return v.data						# return the data put back together again to be sent to browser
	
	# serve file
	if filename[-3:]=="mp3":
		return Response(get_file(filename), mimetype="audio/mpeg", status=200)
	elif filename[-3:]=="wav":
		return Response(get_file(filename), mimetype="audio/wav", status=200)
	else:
		return Response(get_file(filename), status=200, mimetype="audio/mpeg")
	
############ ADMIN PANEL indexes #############

@app.route('/reminders', methods=['GET'])
@app.route('/reminders/<int:page>', methods=['GET'])
@flask_login.login_required
def serve_reminder_admin(page=1):
	'''GUI: this serves an index of the currently scheduled secure messages going out'''
	reminders = Reminder.query.order_by(Reminder.id.desc()).paginate(page,2000,False)
	return render_template("reminders.html", 
				reminders = reminders, 
				recordings_base = recordings_base)

@app.route('/intents', methods=['GET'])
@flask_login.login_required
def serve_intent_admin():
	'''GUI: serve the intents/routing page'''
        intents = Intent.query
        return render_template("intents.html",
                                intents = intents)

@app.route('/assignments', methods=['GET'])
@app.route('/assignments/<int:page>', methods=['GET'])
@flask_login.login_required
def serve_assignment_admin(page=1):
	'''GUI: serve the phone number assignments page'''
        assignments = Assignment.query.order_by(Assignment.id.desc()).paginate(page,2000,False)
        return render_template("assignments.html",
                                assignments = assignments)

@app.route('/calls', methods=['GET'])
@app.route('/calls/<int:page>', methods=['GET'])
@flask_login.login_required
def serve_call_admin(page=1):
	'''GUI: serve the call log page'''
	# TODO: need to add pagination to this!!!
        calls = Call.query.order_by(desc(Call.id)).paginate(page, 200, False)
        return render_template("calls.html",
                                calls = calls)

@app.route('/voicemails', methods=['GET'])
@app.route('/voicemails/<int:page>', methods=['GET'])
@flask_login.login_required
def serve_vm_admin(page=1):
	'''GUI: serve the voicemails page'''
	# TODO: need to add pagination to this!!!
        voicemails = Voicemail.query.order_by(desc(Voicemail.id)).paginate(page, 100, False)
	for vm in voicemails.items:
		vm.intent = Intent.query.filter_by(digit=vm.intent).first().description
        return render_template("voicemails.html",
                                voicemails = voicemails, 
				recordings_base = recordings_base)

@app.route('/audiofiles', methods=['GET'])
@flask_login.login_required
def serve_audio_admin():
	filearray = []
	for root, dirs, files in os.walk('/var/wsgiapps/ehhapp_twilio/assets/audio/'):
		for file_ in files:
			if '.' != file_[0]:
				filearray.append(file_)
	filearray = sorted(filearray)
	return render_template('audiofiles.html',
				audiofiles = filearray)

######## reminders:funcs #############

@app.route('/reminders/<int:remind_id>/delete', methods=['GET'])
@flask_login.login_required
def delete_reminder(remind_id):
	'''GUI: delete a secure message from the DB'''
	record = Reminder.query.get(remind_id)
	if record == None:
		flash('Could not find reminder in database.')
		return redirect(url_for('serve_vm_admin'))
	else:
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_vm_admin'))				

######### assignments:funcs ###########

@app.route('/assignments/edit', methods=['GET', 'POST'])
@flask_login.login_required
def add_assignment():
	'''GUI: add an assignment to the DB'''
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
	'''GUI: edit an assignment in the DB'''
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

@app.route('/assignments/delete<int:assign_id>', methods=['GET'])
@flask_login.login_required
def delete_assignment(assign_id):
	'''GUI: delete an assignment from the DB'''
	record = Assignment.query.get(assign_id)
	if record == None:
		flash('Could not find assignment in database.')
		return redirect(url_for('serve_assignment_admin'))
	else:
		flash('Assignment removed.')
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_assignment_admin'))				

########## intents:funcs ############

@app.route('/intents/edit', methods=['GET', 'POST'])
@flask_login.login_required
def add_intent():
	'''GUI: add an intent/route to the DB'''
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
	'''GUI: edit an intent in the DB'''
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

@app.route('/intents/test<int:intent_id>', methods=['GET', 'POST'])
@flask_login.login_required
def test_intent(intent_id):
	'''GUI: test the routings from the intents to see which people in EHHOP/schedule VMs/calls will go to'''
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
		interresult = db.lookup_name_in_schedule(pos, getlastSatDate())
		for i in interresult:
			phone = db.lookup_phone_by_name(i)
			assignresult[pos].append([i, phone])
		flash(pos + ": " + str(assignresult[pos]))
	return redirect(url_for('serve_intent_admin'))

@app.route('/intents/delete<int:intent_id>', methods=['GET'])
@flask_login.login_required
def delete_intent(intent_id):
	'''GUI: delete an intent from the DB'''
	record = Intent.query.get(intent_id)
	if record == None:
		flash('Could not find route in database.')
		return redirect(url_for('serve_intent_admin'))
	else:
		flash('Route removed.')
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_intent_admin'))				

############# calls:funcs #############

@app.route('/calls/callback', methods=['GET', 'POST'])
def add_call():
	'''API: add a call record to the DB via Twilio Status Callback'''
	twilio_client_key = request.values.get('key', None)		# used to auth requests coming from Twilio
	if twilio_server_key != twilio_client_key:
		if not flask_login.current_user.is_authenticated:	# block unwanted people from adding records
			return app.login_manager.unauthorized()

	call_sid = request.values.get('CallSid', None)	
	from_phone = request.values.get('From', None)
	to_phone = request.values.get('To', None)
	duration = request.values.get('CallDuration', None)
	direction = request.values.get('Direction', None)
	status = request.values.get('CallStatus', None)

	time_now = datetime.now(pytz.timezone('US/Eastern'))
	subtime=timedelta(seconds=int(duration)) if duration != None else timedelta(seconds=5)
	starttime = (time_now-subtime).strftime('%-m/%-d/%Y %H:%M:%S')

	call = Call(call_sid = call_sid,
		    from_phone = from_phone,
		    to_phone = to_phone,
		    time = starttime,
		    duration = duration,
	            direction = direction,
		    status = status)

	# commit record to DB
	db_session.add(call)
	db_session.commit()	
	
	return "Call record added successfully."


@app.route('/calls/delete<int:call_id>', methods=['GET'])
@flask_login.login_required
def delete_call(call_id):
	'''GUI: delete a call record from the DB'''
	if app.debug == False:
		return "Delete not allowed in production.", 403
	record = Call.query.get(call_id)
	if record == None:
		flash('Could not find call record in database.')
		return redirect(url_for('serve_call_admin'))
	else:
		flash('Call record removed.')
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_call_admin'))				

############ recordings:funcs ##############

def add_voicemail(recording_name, ani=None, intent=None, requireds=None, assigns=None):
	'''Internal function to accept incoming VMs and store them in DB'''
	time_now = datetime.now(pytz.timezone('US/Eastern'))
	record = Voicemail(intent=intent,
			   from_phone=ani,
			   time=time_now.strftime('%-m/%-d/%Y %H:%M:%S'),
			   message=recording_name,
			   requireds=requireds,
			   assigns=assigns)
	db_session.add(record)
	db_session.commit()
	return record.id

@app.route('/voicemails/edit<int:record_id>', methods=['GET', 'POST'])
@flask_login.login_required
def edit_voicemail_assignment(record_id):
	'''GUI: edit a VM assignment'''
	vm = Voicemail.query.get(record_id)
	form = VoicemailForm(request.form, obj=vm)
	if request.method == 'POST' and form.validate():
		vm.assigns = form.assigns.data
		db_session.add(vm)
		db_session.commit()
		flash('VM assignment edited.')
		return redirect(url_for('serve_vm_admin'))
	return render_template("intent_form.html", action="Edit", data_type="assignment", form=form)


@app.route('/voicemails/delete<int:record_id>', methods=['GET'])
@flask_login.login_required
def delete_vm(record_id):
	'''GUI: delete a voicemail from the DB'''
	if app.debug == False:
		return "Delete not allowed in production.", 403
	record = Voicemail.query.get(record_id)
	if record == None:
		flash('Could not find VM record in database.')
		return redirect(url_for('serve_vm_admin'))
	else:
		flash('Voicemail removed.')
		db_session.delete(record)
		db_session.commit()
		return redirect(url_for('serve_vm_admin'))				

#========== audiofiles: funcs ================

@app.route('/audiofiles/edit/<audio_name>', methods=['GET', 'POST'])
@flask_login.login_required
def edit_audio(audio_name):
	'''GUI: edit an audiofile'''
	audio_dirname = '/var/wsgiapps/ehhapp_twilio/assets/audio/'
	if find(audio_name, audio_dirname) == None:
		flash('No audiofile (with name: ' + audio_name + ') found.')
		return redirect(url_for('serve_audio_admin'))
	formout = AudiofileForm(audio_file_name=audio_name)
	form = AudiofileForm(request.form)
	if request.method == 'POST' and form.validate():
		form.audio_file.data = request.files['audio_file']
		if form.audio_file.data:
			if request.form['audio_file_name'] == audio_name:
				shutil.move(os.path.join(audio_dirname,audio_name), os.path.join(audio_dirname, audio_name + "_" + randomword(8) + ".bak"))
			form.audio_file.data.save(audio_dirname + audio_name)
		if request.form['audio_file_name'] != audio_name:
			 shutil.move(os.path.join(audio_dirname,audio_name), os.path.join(audio_dirname, request.form['audio_file_name']))
		flash('Audiofile edited.')
		return redirect(url_for('serve_audio_admin'))
	return render_template("intent_form.html", action="Edit", data_type=audio_name, form=formout)

@app.route('/audiofiles/add', methods=['GET', 'POST'])
@flask_login.login_required
def add_audio():
	'''GUI: add an audiofile'''
	audio_dirname = '/var/wsgiapps/ehhapp_twilio/assets/audio/'
	form = AudiofileForm(request.form)
	if request.method == 'POST' and form.validate():
		form.audio_file.data = request.files['audio_file']
		if form.audio_file.data:
			form.audio_file.data.save(audio_dirname + request.form['audio_file_name'])
			flash('Audiofile added.')
		else:
			flash('Error: No audiofile uploaded.')
		return redirect(url_for('serve_audio_admin'))
	return render_template("intent_form.html", action="Add", data_type=" an audiofile", form=form)

@app.route('/audiofiles/delete/<audio_name>', methods=['GET', 'POST'])
@flask_login.login_required
def delete_audio(audio_name):
	'''GUI: delete audio file'''
	audio_dirname = '/var/wsgiapps/ehhapp_twilio/assets/audio/'
	if find(audio_name, audio_dirname) == None:
		flash('No audiofile (with name: ' + audio_name + ') found.')
		return redirect(url_for('serve_audio_admin'))
	os.remove(os.path.join(audio_dirname,audio_name))
	flash('Audiofile deleted.')
	return redirect(url_for('serve_audio_admin'))

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

def randomword(length):
        '''generate a random string of whatever length, good for filenames'''
        return ''.join(random.choice(string.lowercase) for i in range(length))


# END
		

