#!/usr/bin/python 

import ehhapp_twilio
import unittest
from flask import Flask
from flask.ext.testing import LiveServerTestCase
import urllib2
import time
routes = ["/",
	"/dial_extension",
	"/dial_extension?Digits=8144",
	"/next_clinic/CM%201/",
	"/find_person/Twilio/",
	"/handle_key/hello?Digits=1",
	"/handle_key/hello?Digits=2",
	"/handle_key/hello?Digits=3",
	"/handle_key/hello?Digits=*",
	"/handle_key/clinic_open_menu",
	"/handle_key/clinic_open_menu?Digits=1",
	"/handle_key/clinic_open_menu?Digits=2",
	"/handle_key/clinic_closed_menu",
	"/handle_key/clinic_closed_menu?Digits=2",
	"/take_message/0",
	"/take_message/1",
	"/take_message/2",
	"/take_message/3",
	"/handle_key/sp/clinic_open_menu",
	"/handle_key/sp/clinic_open_menu?Digits=1",
	"/handle_key/sp/clinic_open_menu?Digits=2",
	"/handle_key/sp/clinic_closed_menu",
	"/handle_key/sp/clinic_closed_menu?Digits=2",
	"/sp/take_message/0",
	"/sp/take_message/1",
	"/sp/take_message/2",
	"/sp/take_message/3",
	"/auth_menu",
	"/auth_menu?Digits=12345678",
	"/auth_selection",
	"/auth_selection?Digits=1",
	"/auth_selection?Digits=2",
	"/auth_selection?Digits=3",
	"/auth_selection?Digits=4",
	"/caller_id_dial?Digits=1234567890",
	"/caller_id_redial/1234567890",
	"/flashplayer",
	"/play_recording"
]

class HelloTest(unittest.TestCase):

    def setUp(self):
        app = ehhapp_twilio.app
        app.config['TESTING'] = True
	app.config['LIVESERVER_PORT'] = 5000
	app.debug = True
	self.app = ehhapp_twilio.app.test_client()

    def test_all_routes(self):
	print "testing..."
	for r in routes:
		response = self.app.get(r)
		print r, response.status_code
		assert response.status_code in [200, 302]
	pass


if __name__ == '__main__':
	unittest.main()
