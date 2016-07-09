#!/usr/bin/env python

"""
Deployment Script

Run when you are cloning this repo for the first time in a
new production or development environment.

(If you suspect something wrong with this script just
deploy the old-fashioned way - manually)

The steps to deployment are as follows:

    1. Use correct Python version
    2. Be in a directory with ehhapp_twilio/ in it
    3. Be in a directory with venv/ in it
    4. Have dependencies satisfied
    5. Core tests are satisified
    6. Get cron jobs running

HOW TO READ

We import a whole bunch of modules that help us
learn about the deployment environment. We also 
throw the call method in so we can issue shell 
commands, and the DistributionNotFound exception 
so we can handle it when checking whether 
dependencies are satisfied (see step 4 above).

We read requirements.txt and define an install 
function that installs requirements for us.

The rest of the code steps through deployment 
making generous use of if conditions for 
control flow.

At the end of the day, the app should be 
deployed correctly within its directory 
with the only steps remaining for the sys admin 
being to configure a web server correctly to 
run a WSGI-compliant application.
"""

import os                 # miscellaneous OS functions
import sys                # getting interpreter data
import errno              # standard error messages
import site               # site-package functions
import pkg_resources      # from setuptools for package introspection

# shell commands
from subprocess import call

# package introspection
from pkg_resources import DistributionNotFound

################################
# Read file, Define a function #
################################

# Local file I/O, gets requirements as a list
requirements = []
with open('requirements.txt') as f:
    for line in f.readlines():
        requirements.append(line.rstrip())

# Function definitions
def installrequirements():
    current_working_directory = os.getcwd()
    venv_dir = '{}/venv'.format(current_working_directory)
    if venv_dir in site.PREFIXES:
        print("The Virtual environment is active.\nInstalling requirements.")
        call(['pip', 'install', '-r', 'requirements.txt'], shell=True)
    else:
        print("Activating virtual environment AND installing requirements.")
        call(['source venv/bin/activate && pip install -r requirements.txt'], shell=True)

##########
# Deploy #
##########

# Are we using the correct Python version?
majv, minv, micv, rl, ser = sys.version_info
if (majv, minv, micv) == (2, 7, 11):
    print("This script is being run using Python 2.7.11. Good.")
else:
    error = os.strerror(errno.EPERM)
    message = "You are running an incompatible Python version: {}.{}.{}".format(majv, minv, micv)
    raise OSError((error, message))

# Take stock of the current working directory.
dir_files = os.listdir('.') # current working directory as a list

# Does it have ehhapp_twilio in it?
if 'ehhapp_twilio' in dir_files:
    print("We are in the correct directory (ehhapp_twilio is here).")
else:
    raise OSError("This script is being run in the wrong directory.")

# Does it have a virtualenv set up?
if 'venv' in dir_files:
    print("Virtual environment already created. It is called `venv`.")
else:
    # set up virtualenv
    print("No Virtual Environment\nCreating now...")
    call(['virtualenv', 'venv'])

# Are all dependencies available?
print("Are all dependencies available?")
try:
    pkg_resources.require(requirements)
    print("We good.")
except DistributionNotFound:
    print("Guess not. Installing now.")
    installrequirements()

# Are all of our core application logic tests passing?
call(['py.test', 'tests.py'])
print("Passed? Great, use `python run.py` or deploy to web.\
        \nElse, work out those kinks.")

