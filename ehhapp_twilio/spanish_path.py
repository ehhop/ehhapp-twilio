#!/usr/bin/python
from ehhapp_twilio import *
from ehhapp_twilio.database_helpers import *

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
