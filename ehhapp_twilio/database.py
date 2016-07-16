from ehhapp_twilio import *
from flask_sqlalchemy import SQLAlchemy
from ehhapp_twilio.config import *

db = SQLAlchemy(app)

# import a db_session to query db from other modules
db_session = db.session
