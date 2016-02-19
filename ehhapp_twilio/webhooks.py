import requests, json
from ehhapp_twilio.config import *

def slack_notify(msg, uname=slack_user, icon=slack_icon, cn=slack_channel, hookurl = hookurl):
	payload = {'text': msg, 
		'username': uname, 
		'icon_emogi':icon, 
		'channel': cn}
	payload_json = json.dumps(payload)
	requests.post(hookurl, data=payload_json)
	return None
