import sys, os, pytz, re, ftplib
from datetime import datetime, timedelta, date, time
#temporary DB for outgoing messages
import dataset
#flask stuff
from flask import Flask, request, redirect, send_from_directory, Response, stream_with_context, url_for, render_template
import flask.ext.login as flask_login
from flask_sqlalchemy import SQLAlchemy
#delayed messages
from celery import Celery
#Google Sign Ins
from oauth2client import client as gauthclient
from oauth2client import crypt

#other helpers
base_dir = os.path.dirname(os.path.realpath(__file__))
execfile(base_dir + "/gdatabase.py")
execfile(base_dir + "/email_helper.py")

#Twilio
import twilio.twiml
from twilio.rest import TwilioRestClient
client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)

#Flask init
app = Flask(__name__, static_folder='')
app.config['CELERY_BROKER_URL'] = 'redis://:' + redis_pass + '@localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://:' + redis_pass + '@localhost:6379/0'
app.config['CELERY_ENABLE_UTC'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/wsgiapps/ehhapp-twilio/ehhapp-twilio-2.db'
app.secret_key = flask_secret_key
app.debug = True

#SQLAlchemy
db2 = SQLAlchemy(app)

#logins
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

#delayed messages init
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# user/pass to log into Twilio to retrieve files
auth_combo=HTTPBasicAuth(twilio_AccountSID, twilio_AuthToken)

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
			g.play("https://s3.amazonaws.com/ehhapp-phone/welcome_greeting_ehhop.mp3")
			g.pause(length=5)
	return str(resp)

@app.route("/handle_key/hello", methods=["GET", "POST"])
def handle_key_hello():
	'''respond to initial direction'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)
	#get day of week (0 is Monday and 6 is Sunday)
	day_of_week = datetime.now(pytz.timezone('US/Eastern')).weekday()
		
	if digit == '1':
		'''instructions in english selected'''
		if day_of_week == 5: #clinic is open on Saturdays
			with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
				
				#If you have an appointment today, please press 1. 
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
				#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
				#If you are an EHHOP patient and have a question about a bill you received, please press 6.
				#For all other non-urgent concerns, please press 7.
				#To hear this menu again, stay on the line.
				for i in range(0,3):
					g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
					g.pause(length=5)
		else:
			with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g:
				
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
				#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
				#If you are an EHHOP patient and have a question about a bill you received, please press 6.
				#For all other non-urgent concerns, please press 7.
				#To hear this menu again, stay on the line.
				for i in range(0,3):
					g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3")
					g.pause(length=5)
					
	elif digit == '2':
		'''instructions in spanish selected'''
		# spanish: if this is an emerg, dial 911
		resp.play('https://s3.amazonaws.com/ehhapp-phone/sp_emerg_911.mp3')
		if day_of_week == 5: #clinic is open on Saturdays
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
				# spanish: list options 1-4 similar to english
				for i in range(0,3):
					g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
					g.pause(length=5)
		else: #clinic not open
			with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g:
				# spanish: list options 2-4 similar to english
				for i in range(0,3):
					g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_closed_menu.mp3')
					g.pause(length=5)
	elif digit == "3": 
		'''extension feature'''
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/pleasedial4digit.mp3')
		
	elif digit == '*':
		'''auth menu'''
		with resp.gather(numDigits=8, action='/auth_menu', method="POST") as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/enterpasscode.mp3')
	
	else:
		'''They have pressed an incorrect key.'''
		return redirect('/')
	
	return str(resp)

@app.route("/dial_extension", methods=["GET", "POST"])
def dial_extension():
	resp = twilio.twiml.Response()
	digits = request.values.get('Digits', None)
	database = EHHOPdb(credentials)
	try:
		return_num = database.lookup_phone_by_extension(int(digits))
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/couldntfindext.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/pleasedial4digit.mp3')
		return str(resp)
	if return_num == None:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/couldntfindext.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=4, action="/dial_extension", method="POST") as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/pleasedial4digit.mp3')
	else:
		resp.say("Sending you to the mailbox of " + return_num[0], voice='alice', language='en-US')
		resp.pause(length=1)
		resp.redirect('/take_message/0?to_email=' + return_num[2])
	return str(resp)

@app.route("/next_clinic/<person_type>/", methods=["GET", "POST"])
def find_in_schedule(person_type):
	resp = twilio.twiml.Response()
	database = EHHOPdb(credentials)
	return_num = None
	try:
		return_names = database.lookup_name_in_schedule(person_type, getSatDate())
		if return_names != []:
			return_num = database.lookup_phone_by_name(return_names[0])
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/systemfailure.mp3')
		return str(resp)
		
	if return_names == []:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/couldntfindpersonindb.mp3')
	else:
		for name in return_names:
			return_num = database.lookup_phone_by_name(name)
			if return_num != None:
				resp.say("Connecting you with " + name, voice='alice', language='en-US')
				resp.pause(length=3)
				resp.dial(return_num, callerId='+18622425952')
		resp.play('https://s3.amazonaws.com/ehhapp-phone/callfailed-goodbye.mp3')
	return str(resp)

@app.route("/find_person/<person_type>/", methods=["GET", "POST"])
def find_person(person_type):
        resp = twilio.twiml.Response()
        database = EHHOPdb(credentials)
        return_num = None
        try:
                return_nums = database.lookup_name_by_position(person_type)      
        except:
                resp.play('https://s3.amazonaws.com/ehhapp-phone/systemfailure.mp3')
                return str(resp)

        if return_num == []:
                resp.play('https://s3.amazonaws.com/ehhapp-phone/couldntfindpersonindb.mp3')
        else:
                for return_num in return_nums:
                        if return_num != None:
                                resp.say("Connecting you with " + return_num[0], voice='alice', language='en-US')
                                resp.pause(length=3)
                                resp.dial(return_num[1], callerId='+18622425952')
                resp.play('https://s3.amazonaws.com/ehhapp-phone/callfailed-goodbye.mp3')
        return str(resp)
	
@app.route("/handle_key/clinic_open_menu", methods=["GET", "POST"])
def clinic_open_menu():
	'''respond to digit press when the clinic is open
	1 - appt today
	2 - not been here before
	3 - urgent concern and ehhop patient
	4 - ehhop pt with question
	'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)

	# get the phone # of the on call - fallback if something wrong
	oncall_current_phone = getOnCallPhoneNum()

	# appointment today
	if digit == '1':
		# now transferring your call
		resp.play("https://s3.amazonaws.com/ehhapp-phone/xfer_call.mp3")
		# dial current CM
		resp.dial(oncall_current_phone)
		# if the call fails
		resp.play('https://s3.amazonaws.com/ehhapp-phone/allbusy_trylater.mp3')
		# replay initial menu
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
				#If you have an appointment today, please press 1. 
				#If you have not been to EHHOP before, please press 2.
				#If you are an EHHOP patient and have an urgent medical concern, please press 3.
				#If you are an EHHOP patient and have a question about medications, appointments, 
				#or other matters, please press 4.
				g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
				g.pause(length=5)
	# not been here before
	elif digit in ['2', '3', '4','5','6','7']:
		return redirect('/take_message/' + digit)
	# accidential key press
	else:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/incorrectkey.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_open_menu", method="POST") as g:
			#If you have an appointment today, please press 1. 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
			#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
			#If you are an EHHOP patient and have a question about a bill you received, please press 6.
			#For all other non-urgent concerns, please press 7.
			#To hear this menu again, stay on the line.
			g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_open_menu.mp3")
			g.pause(length=5)
	return str(resp)

@app.route("/handle_key/clinic_closed_menu", methods=["GET", "POST"])
def clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)
	
	if intent in ['2','3','4','5','6','7']:
		return redirect("/take_message/" + intent)
	else:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/incorrectkey.mp3')
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/clinic_closed_menu", method="POST") as g: 
			#If you have not been to EHHOP before, please press 2.
			#If you are an EHHOP patient and have an urgent medical concern, please press 3.
			#If you are an EHHOP patient and have a question about an upcoming appointment or medications, please press 4.
			#If you are an EHHOP patient and would like to schedule an appointment with a specialist, opthamology, or dental, please press 5.
			#If you are an EHHOP patient and have a question about a bill you received, please press 6.
			#For all other non-urgent concerns, please press 7.
			#To hear this menu again, stay on the line.
			g.play("https://s3.amazonaws.com/ehhapp-phone/clinic_closed_menu.mp3")
			g.pause(length=5)
	return str(resp)
	
@app.route("/take_message/<int:intent>", methods=['GET', 'POST'])
def take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	
	resp = twilio.twiml.Response()
	if intent == 0:
		to_email = request.values.get('to_email', None)
		after_record = '/handle_recording/' + str(intent) + '?to_email=' + to_email
	else:
		after_record = '/handle_recording/' + str(intent)
	
	if intent == '3':
		#Please leave a message for us after the tone. Make sure to let us know what times we can call you back. We will call you back as soon as possible.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/urgent_message.mp3")
	else:
		#Please leave a message for us after the tone. Make sure to let us know what times we can call you back. We will call you back within one day.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/nonurgent_message.mp3")

	resp.play("https://s3.amazonaws.com/ehhapp-phone/vm_instructions.mp3")

	# after patient leaves message, direct them to next step
	
	resp.record(maxLength=300, action=after_record, method="POST")

	return str(resp)

@app.route("/handle_recording/<int:intent>", methods=['GET', 'POST'])
def handle_recording(intent):
	'''patient has finished leaving recording'''
	resp = twilio.twiml.Response()
	ani = request.values.get('From', 'None')
	to_email = None
	positions = None
	if intent == 0:
		to_email = request.values.get('to_email', None)
	else:
		positions = ','.join(intentions[intent][1])
	recording_url = request.values.get("RecordingUrl", None)

	# process message asynchronously (e.g. download and send emails) using Celery
	async_process_message.delay(recording_url, intent, ani, positions, to_emails=to_email)

	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sent_message.mp3")
	return str(resp)

################# spanish path ###############

@app.route("/handle_key/sp/clinic_open_menu", methods=["GET", "POST"])
def sp_clinic_open_menu():
	'''respond to digit press when the clinic is open
	1 - appt today
	2 - not been here before
	3 - urgent concern and ehhop patient
	4 - ehhop pt with question
	'''
	resp = twilio.twiml.Response()
	digit = request.values.get('Digits', None)
	
	# get the phone # of the on call - fallback if something wrong
	oncall_current_phone = getOnCallPhoneNum()
	
	# appointment today
	if digit == '1':
		# now transferring your call
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_xfer_call.mp3")
		# dial current CM
		resp.dial(oncall_current_phone)
		# if the call fails
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_try_again.mp3")
		# replay initial menu
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
			# spanish: list options 1-4 similar to english
			for i in range(0,3):
				g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
				g.pause(length=5)
	# not been here before
	elif digit in ['2', '3', '4']:
		return redirect('/sp/take_message/' + digit)
	# accidential key press
	else:
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_incorrect_key.mp3")
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_open_menu", method="POST") as g:
			# spanish: list options 1-4 similar to english
			for i in range(0,3):
				g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_open_menu.mp3')
				g.pause(length=5)
	return str(resp)

@app.route("/handle_key/sp/clinic_closed_menu", methods=["GET", "POST"])
def sp_clinic_closed_menu():
	'''what to do if the clinic is closed'''
	resp = twilio.twiml.Response()
	intent = request.values.get('Digits', None)
	
	if intent in ['2','3','4']:
		return redirect("/sp/take_message/" + intent)
	else:
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_incorrect_key.mp3")
		resp.pause(length=3)
		with resp.gather(numDigits=1, action="/handle_key/sp/clinic_closed_menu", method="POST") as g:
			# spanish: list options 2-4 similar to english
			for i in range(0,3):
				g.play('https://s3.amazonaws.com/ehhapp-phone/sp_clinic_closed_menu.mp3')
				g.pause(length=5)
	return str(resp)
	
@app.route("/sp/take_message/<intent>", methods=['GET', 'POST'])
def sp_take_message(intent):
	'''takes a voice message and passes it to the voicemail server'''
	
	resp = twilio.twiml.Response()
	
	if intent == '3':
		#spanish: Please leave a message for us after the tone. We will call you back as soon as possible.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_urgent_message.mp3")
	if intent in ['2','4']:
		#spanish: Please leave a message for us after the tone. We will call you back within one day.
		resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_nonurgent_message.mp3")
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_vm_instructions.mp3")

	# save recording after received at next step
	after_record = '/sp/handle_recording/' + intent
	resp.record(maxLength=300, action=after_record, method="POST")
	
	return str(resp)

@app.route("/sp/handle_recording/<int:intent>", methods=['GET', 'POST'])
def sp_handle_recording(intent):
	'''patient has finished leaving recording'''
        resp = twilio.twiml.Response()
        ani = request.values.get('From', 'None')
        recording_url = request.values.get("RecordingUrl", None)

        # process message (e.g. download and send emails)
	async_process_message.delay(recording_url, intent, ani)
	
	###if the message was successfully sent... TODO to check
	# Your message was sent. Thank you for contacting EHHOP. Goodbye!
	resp.play("https://s3.amazonaws.com/ehhapp-phone/sp_sent_message.mp3")
	return str(resp)

#==============SERVE VOICEMAILS============
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
			flask_login.login_user(user, remember=True)
	return useremail
	

@app.route('/flashplayer', methods=['GET'])
def serve_vm_player():
	audio_url = request.values.get('a', None)
	return render_template("player_twilio.html",
							audio_url = audio_url)

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
		session = ftplib.FTP('ftp.box.com', box_username, box_password)
		session.retrbinary('RETR recordings/' + filename, chunks.append)
		session.close()
		for chunk in chunks:
			yield chunk
	
	# serve file
	return Response(get_file(filename), mimetype='audio/wav')

#==============authenticated menu============
@app.route("/auth_menu", methods=['GET','POST'])
def auth_menu():
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)
	
	if passcode == '12345678':
		#success
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			#To call Pacific Interpreters, please press 1.
			#To dial a patient using the ehhop number, please press 2.
			#To leave a secure message for a patient, please press 3. 			
			g.play('https://s3.amazonaws.com/ehhapp-phone/dial-vmremindermenu.mp3')
		return str(resp)
	else:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/incorrectkey.mp3')
		with resp.gather(numDigits=8, action='/auth_menu', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/enterpasscode.mp3')
		return str(resp)

@app.route("/auth_selection", methods=['GET','POST'])
def auth_selection():
	resp = twilio.twiml.Response()
	digit = request.values.get("Digits", None)
	
	if digit == '1':
		resp.dial('+18002641552', callerId='+18622425952')
		return str(resp)
	elif digit == '2':
		with resp.gather(numDigits=10, action='/caller_id_dial', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/entertodigits.mp3')
		return str(resp)
	elif digit == '3':
		with resp.gather(numDigits=10, action='/secure_message/setnum/', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/entertendigits-vm.mp3')
		return str(resp)
	else:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/incorrectkey.mp3')
		with resp.gather(numDigits=1, action='/auth_selection', method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/dial-vmremindermenu.mp3')
                return str(resp)

@app.route("/secure_message/setnum/", methods=['GET', 'POST'])
def secure_message_setnum():
	''' creates a row in the database with a secure message ID and pt phone num
	    still need to set the following:
		reminder time (now, one day from now, or specify date)
		reminder frequency (default = one day if they dont pick up)
		message
		recorded name
		spanish?
		passcode
	'''
	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)
	from_phone=request.values.get("From", None)
	
	db = open_db()	
	r = db['reminders']
	# add phone number to reminders, move to next step
	remind_id = r.insert(dict(to_phone=number, 
			from_phone=from_phone,
			time=None,
			delivered=False,
			freq=24,
			message=None,
			name=None,
			passcode=None,
			spanish=None))
	
	with resp.gather(numDigits=6, action='/secure_message/setpass/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/youdialed.mp3')
		g.say(' '.join(number) + '. ', voice='alice')
		g.play('https://s3.amazonaws.com/ehhapp-phone/setpass.mp3')
	return str(resp)

@app.route("/secure_message/setpass/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_setpass(remind_id):
	''' sets the passcode from the last step and asks for a reminder time '''
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']

	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)

	# set a passcode and update the DB
	record['passcode'] = passcode
	r.update(record, ['id'])

	# ask for a reminder time
	with resp.gather(numDigits=1, action='/secure_message/settime/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/youdialed.mp3')
		g.say(' '.join(passcode) + ".", voice="alice")
		g.play('https://s3.amazonaws.com/ehhapp-phone/settime.mp3')
	return str(resp)

@app.route("/secure_message/settime/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_settime(remind_id):
	''' sets the reminder time and asks for the message '''
	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)
	
	# set the reminder time delta
	nowtime = datetime.now()
	time_set = None
	if choice == '2':
		# set the time for tomorrow
		time_set = datetime.combine(nowtime.date() + timedelta(1), time(10,0,0,1))
	else:
		# set the time as now
		time_set = nowtime
	
	# set the reminder time and update the DB
	record['time'] = str(time_set)
        r.update(record, ['id'])
	
	# now we need to record the message
	resp.play('https://s3.amazonaws.com/ehhapp-phone/leavesecuremessage.mp3')
	resp.record(maxLength=300, action="/secure_message/setmessage/" + str(remind_id), method='POST')

	return str(resp)

@app.route("/secure_message/setmessage/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_setmessage(remind_id):
	resp = twilio.twiml.Response()
	recording_url = request.values.get("RecordingUrl", None)
	
	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)

	# set a new save file name randomly
	save_name = randomword(128) + ".wav"
	# set the secure recording URL location
	new_recording_url = 'https://twilio.ehhapp.org/play_recording?filename=' + save_name
	# set the message url and update the db
	record['message'] = new_recording_url
        r.update(record, ['id'])

	# download and save the message (async)
	save_secure_message.apply_async(args=[recording_url, save_name])

	with resp.gather(numDigits=1, action='/secure_message/send/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/confirmsecuremessage.mp3')
	return str(resp)

@app.route("/secure_message/send/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_send(remind_id):
	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/vmsystemfail.mp3')
		return str(resp)
	
	# we should have everything now, so make a record in celery for a call out
	set_async_message_deliver(record, remind_id)
	
	resp.play('https://s3.amazonaws.com/ehhapp-phone/securemessagesent.mp3')
	return str(resp)

@app.route("/secure_message/callback/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_callback(remind_id):
	resp = twilio.twiml.Response()

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/hello_importantmessage.mp3')
		resp.play('https://s3.amazonaws.com/ehhapp-phone/messageretrievalfail.mp3')
		return str(resp)
	
	with resp.gather(numDigits=1, action='/secure_message/passauth/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/hello_importantmessage.mp3')
		g.play('https://s3.amazonaws.com/ehhapp-phone/pressanynumtohearmessage.mp3')
	return str(resp)		

@app.route("/secure_message/passauth/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_passauth(remind_id):
	resp = twilio.twiml.Response()
	choice=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	try:
		# find the record in the DB that corresponds to this call
		record = r.find_one(id=remind_id)
	except:
		resp.play('https://s3.amazonaws.com/ehhapp-phone/messageretrievalfail.mp3')
		return str(resp)

	with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/pleaseenterpasscoderetrieve.mp3')
	return str(resp)

@app.route("/secure_message/playback/<int:remind_id>", methods=['GET', 'POST'])
def secure_message_playback(remind_id):
	resp = twilio.twiml.Response()
	passcode=request.values.get("Digits", None)

	db = open_db()	
	r = db['reminders']
	# find the record in the DB that corresponds to this call
	record = r.find_one(id=remind_id)
	
	if record['passcode'] != passcode:
		with resp.gather(numDigits=6, action='/secure_message/playback/' + str(remind_id), method='POST') as g:
			g.play('https://s3.amazonaws.com/ehhapp-phone/passcodeincorrect.mp3')
		return str(resp)
	else:
		record['delivered'] = True
		r.update(record, ['id'])
		deliver_callback.apply_async(args=[remind_id, record['from_phone']])
		resp.play('https://s3.amazonaws.com/ehhapp-phone/pleasewaittohearmessage.mp3')
		resp.play(record['message'])
		resp.play('https://s3.amazonaws.com/ehhapp-phone/messagewillrepeat.mp3')
		resp.play(record['message'], loop=5)
		resp.play('https://s3.amazonaws.com/ehhapp-phone/goodbye.mp3')
		return str(resp)

@app.route("/secure_message/delivered/<int:remind_id>", methods=["GET", "POST"])
def secure_message_delivered(remind_id):
	resp = twilio.twiml.Response()

	db = open_db()
	r = db['reminders']
	# find the record in the DB that corresponds to this call
	record = r.find_one(id=remind_id)
	
	resp.play('https://s3.amazonaws.com/ehhapp-phone/deliverpart1.mp3')
	resp.say(' '.join(record["to_phone"]))
	resp.play('https://s3.amazonaws.com/ehhapp-phone/deliverpart2.mp3')
	return str(resp)


@app.route("/caller_id_dial", methods=['GET','POST'])
def caller_id_dial():
	''' dials out from the EHHOP phone number'''

	resp = twilio.twiml.Response()
	number=request.values.get("Digits", None)

	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/tryagainpress1.mp3')
	return str(resp)
	
@app.route("/caller_id_redial/<number>", methods=['GET','POST'])
def caller_id_redial(number):
	'''redials a number dialed out by caller_id_dial - digits only dialed once'''

	resp = twilio.twiml.Response()
	resp.say("Connecting you with your destination.", voice='alice')
	resp.dial("+1" + number, callerId='+18622425952')
	resp.say("I'm sorry, but your call either failed or may have been cut short.", voice='alice', language='en-US')

	with resp.gather(numDigits=1, action='/caller_id_redial/' + number, method='POST') as g:
		g.play('https://s3.amazonaws.com/ehhapp-phone/tryagainpress1.mp3')
	return str(resp)

#==============OTHER HELPERS===============

def getSatDate():
        # get next saturday's date
        time_now = datetime.now(pytz.timezone('US/Eastern'))
        day_of_week = time_now.weekday()
        addtime = None
        if day_of_week == 6:
                addtime=timedelta(6)
        else:
                addtime=timedelta(5-day_of_week)
        satdate = (time_now+addtime).strftime('%-m/%-d/%Y')
        return satdate

def open_db():
	db = dataset.connect('sqlite:///var/wsgiapps/ehhapp-twilio/ehhapp-twilio.db')
	return db

#==============BACKGROUND TASKS==============

@celery.task(name='tasks.async_process_message')
def async_process_message(recording_url, intent, ani, positions, to_emails=None):
	process_recording(recording_url, intent, ani, positions, to_emails=to_emails)
	return None

def set_async_message_deliver(record, remind_id):
	deliver_time = datetime.strptime(record['time'],'%Y-%m-%d %H:%M:%S.%f')
	send_message.apply_async(args=[remind_id, record['to_phone']], eta=deliver_time)	
	return None

@celery.task
def save_secure_message(recording_url, save_name):
	# download the file to HIPAA box
	save_file_with_name(recording_url, auth_combo, save_name)
	return None

@celery.task
def send_message(remind_id, to_phone):
	execfile(base_dir + "/gdatabase.py")
	execfile(base_dir + "/email_helper.py")
	from twilio.rest import TwilioRestClient
	client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/callback/" + str(remind_id),
		to = to_phone,
		from_ = twilio_number,
	)
	return None

@celery.task
def deliver_callback(remind_id, from_phone):
	execfile(base_dir + "/gdatabase.py")
	execfile(base_dir + "/email_helper.py")
	from twilio.rest import TwilioRestClient
	client = TwilioRestClient(twilio_AccountSID, twilio_AuthToken)
	call = client.calls.create(url="https://twilio.ehhapp.org/secure_message/delivered/" + str(remind_id),
		to = from_phone,
		from_ = twilio_number,
	)
	return None

#============MUST BE LAST LINE================
if __name__ == '__main__':
	app.debug = True
	app.run()

