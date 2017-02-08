#!/usr/bin/env python
import sys, os
import site
site.addsitedir('/var/wsgiapps/ehhapp_twilio/venv/lib/python2.7/site-packages')

PROJECT_DIR = '/var/wsgiapps/ehhapp_twilio/'
sys.path.append(PROJECT_DIR)
sys.path.append(PROJECT_DIR + '/venv')

activate_this = os.path.expanduser('/var/wsgiapps/ehhapp_twilio/venv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from ehhapp_twilio.config import *
from ftplib import FTP_TLS
import subprocess

save_name = subprocess.check_output('date +%m%d%y', shell=True).strip('\n') + '-ehhapp-twilio.db'
session = FTP_TLS('ftp.box.com', box_username, box_password)
session.prot_p()
session.storbinary('STOR server/' + save_name, open('ehhapp-twilio.db', 'rb'))
session.quit()
