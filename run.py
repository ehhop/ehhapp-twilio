import sys, os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from ehhapp_twilio import app
app.run(debug=True)
