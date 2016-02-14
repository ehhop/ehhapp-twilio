import sys, os
import site
site.addsitedir('/var/wsgiapps/ehhapp_twilio/venv/lib/python2.7/site-packages')

PROJECT_DIR = '/var/wsgiapps/ehhapp_twilio/'
sys.path.append(PROJECT_DIR)
sys.path.append(PROJECT_DIR + '/venv')

activate_this = os.path.expanduser('/var/wsgiapps/ehhapp_twilio/venv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

# make our Flask app available for mod_wsgi
from ehhapp_twilio import app as application
