#!/usr/bin/python 

"""
Tests

A few parts:
    - Deployment Environment
    - Routes
    - API calls
"""

import urllib2, time, os

# Deployment Environment
def test_redis_is_running():
    print "checking if redis is running... "
    redis_pass = 'redis_pass'
    result = os.popen("redis-cli -a " + redis_pass + " ping").read()
    assert "PONG" in result

# We want to test some routes
routes = ["/?From=1234567890",
    "/dial_extension",
    "/dial_extension?Digits=9999",
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

import ehhapp_twilio
from ehhapp_twilio.config import *
import unittest
from flask import Flask
import flask.ext.login as flask_login
from flask.ext.testing import LiveServerTestCase

class TestConfig(unittest.TestCase):
    
    def test_oauth2_file(self):
        print google_oauth2_file
        assert type(google_oauth2_file) == str

class HelloTest(unittest.TestCase):

    def setUp(self):
        app = ehhapp_twilio.app
        app.config['TESTING'] = True
        app.config['LIVESERVER_PORT'] = 5000
        app.debug = True
        self.app = ehhapp_twilio.app.test_client()
        self.next_step = ''

    def test_all_routes(self):
        print "testing..."
        for r in routes:
            response = self.app.get(r)
            print r, response.status_code
            assert response.status_code in [200, 302]
            pass
     
    def test_celery_VM_upload_download(self):
        print "checking celery and VM downloads"
        upload = ehhapp_twilio.backgroundtasks.async_process_message.apply_async(args=["http://www.kozco.com/tech/piano2.wav", 0, "1234567890", "Twilio"], kwargs={'assign':"rneff@ehhapp.org"})
        assert ".wav" in upload.get()
        download = self.app.get("/play_recording?filename=" + upload.get())
        assert download.status_code in [200, 302]
        assert "Not Authorized" in download.data

    def test_secure_setnum(self):
        response = self.app.get('/secure_message/setnum/?Digits=1234567890&From=9739608144')
        assert response.status_code == 403

if __name__ == '__main__':
    unittest.main(verbosity=2)
