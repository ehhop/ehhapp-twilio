#!/usr/bin/env python
import sys, os
import site
import ehhapp_twilio.python_box_oauth2 as box_api

site.addsitedir('/var/wsgiapps/ehhapp_twilio/venv/lib/python2.7/site-packages')

PROJECT_DIR = '/var/wsgiapps/ehhapp_twilio/'
sys.path.append(PROJECT_DIR)
sys.path.append(PROJECT_DIR + '/venv')

activate_this = os.path.expanduser('/var/wsgiapps/ehhapp_twilio/venv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from ehhapp_twilio.config import *
#from ftplib import FTP_TLS
import subprocess

save_name = subprocess.check_output('date +%m%d%y', shell=True).strip('\n') + '-ehhapp-twilio.db'

print("store file")
box_api.upload_file(source="ehhapp-twilio.db",dest_folder_name="server",dest_file_name=save_name,force=True)
print("completed!")