from ehhapp_twilio.database import db
from ehhapp_twilio.config import *
from sqlalchemy_utils import EncryptedType

# this file - definds sqlalchemy tables in the database, 
# also makes them objects for getting stuff from the DB

class User(db.Model):
    """A user capable of listening to voicemails"""
    __tablename__ = 'user'

    email = db.Column(EncryptedType(db.String, flask_secret_key), primary_key=True)
    google_token = db.Column(EncryptedType(db.String, flask_secret_key))
    authenticated = db.Column(EncryptedType(db.Boolean, flask_secret_key), default=False)

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.email

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False


class Reminder(db.Model):
    """A secure message reminder going out and the associated callback."""
    __tablename__ = 'reminder'

    id = db.Column(db.Integer, primary_key=True)
    to_phone = db.Column(EncryptedType(db.String, flask_secret_key))
    from_phone = db.Column(EncryptedType(db.String, flask_secret_key))
    time = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    delivered = db.Column(EncryptedType(db.Boolean, flask_secret_key), default=False)
    freq = db.Column(EncryptedType(db.Integer, flask_secret_key), default=24)
    message = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    name = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    passcode = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    spanish = db.Column(EncryptedType(db.Boolean, flask_secret_key), default=False)

    def __repr__(self):
        return '<Reminder %r, To: %r, From: %r>' % (self.id, self.to_phone, self.from_phone)

class Voicemail(db.Model):
    """A voicemail from a patient."""
    __tablename__ = 'voicemail'

    id = db.Column(db.Integer, primary_key=True)
    from_phone = db.Column(EncryptedType(db.String, flask_secret_key))
    time = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    intent = db.Column(EncryptedType(db.Integer, flask_secret_key), default=None)
    message = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    requireds = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    assigns = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    view_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String, default="New")
    last_updated_by = db.Column(EncryptedType(db.String, flask_secret_key), default=None)
    caller_id = db.Column(EncryptedType(db.String, flask_secret_key), default=None)

    def __repr__(self):
        return '<Voicemail %r, Time: %r>' % (self.id, self.time)

class Call(db.Model):
	"""A call coming in and any associated voicemail messages."""
	__tablename__ = 'call'
	
	id = db.Column(db.Integer, primary_key=True)
	call_sid = db.Column(db.String)
	from_phone = db.Column(EncryptedType(db.String, flask_secret_key))
	to_phone = db.Column(EncryptedType(db.String, flask_secret_key))
	time = db.Column(EncryptedType(db.String, flask_secret_key))
	duration = db.Column(EncryptedType(db.String, flask_secret_key))
	direction = db.Column(EncryptedType(db.String, flask_secret_key))
	status = db.Column(EncryptedType(db.String, flask_secret_key))
	actions = db.Column(EncryptedType(db.String, flask_secret_key))
	caller_id = db.Column(EncryptedType(db.String, flask_secret_key), default=None)

	def __repr__(self):
		return '<Call %r, From: %r, Time: %r, Length: %r>' % (self.id, self.from_phone, self.time, self.duration)

	def __init__(self, call_sid=None, from_phone=None, to_phone = to_phone, time=None, duration=None, direction=None, status=None, caller_id=None):
		self.call_sid = call_sid
		self.from_phone = from_phone
		self.to_phone = to_phone
		self.time = time
		self.duration = duration
		self.direction = direction
		self.status = status
		self.caller_id = caller_id


class Intent(db.Model):
	__tablename__ = 'intent'
	
	id = db.Column(db.Integer, primary_key=True)
	digit = db.Column(db.Integer)
	description = db.Column(db.String)
	required_recipients = db.Column(db.String)
	distributed_recipients = db.Column(db.String)
	
	def __repr__(self):
		return '<Intent %r, Digit: %r>' % (self.id, self.digit)

	def __init__(self, digit=None, description=None, required_recipients=None, distributed_recipients=None):
		self.digit = digit
		self.description = description
		self.required_recipients = required_recipients
		self.distributed_recipients = distributed_recipients

class Assignment(db.Model):
	__tablename__ = 'assignment'
	
	id = db.Column(db.Integer, primary_key=True)
	from_phone = db.Column(EncryptedType(db.String, flask_secret_key))
	recipients = db.Column(db.String)
	intent = db.Column(db.Integer)

	def __repr__(self):
		return '<Assignment %r>' % (self.id)

	def __init__(self, from_phone=None, recipients=None, intent=None):
		self.from_phone = from_phone
		self.recipients = recipients
		self.intent = intent
