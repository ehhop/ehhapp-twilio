import unittest
import ehhapp_twilio
from flask import Flask
import flask.ext.login as flask_login
from flask.ext.testing import LiveServerTestCase

class RouteTest(unittest.TestCase):

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

