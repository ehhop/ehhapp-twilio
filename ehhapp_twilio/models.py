from sqlalchemy import Column, Integer, String, Boolean
from ehhapp_twilio.database import Base
from ehhapp_twilio.config import *
from sqlalchemy_utils import EncryptedType

class User(Base):
    """A user capable of listening to voicemails"""
    __tablename__ = 'user'

    email = Column(EncryptedType(String, flask_secret_key), primary_key=True)
    google_token = Column(EncryptedType(String, flask_secret_key))
    authenticated = Column(EncryptedType(Boolean, flask_secret_key), default=False)

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


class Reminder(Base):
    """A secure message reminder going out and the associated callback."""
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True)
    to_phone = Column(EncryptedType(String, flask_secret_key))
    from_phone = Column(EncryptedType(String, flask_secret_key))
    time = Column(EncryptedType(String, flask_secret_key), default=None)
    delivered = Column(EncryptedType(Boolean, flask_secret_key), default=False)
    freq = Column(EncryptedType(Integer, flask_secret_key), default=24)
    message = Column(EncryptedType(String, flask_secret_key), default=None)
    name = Column(EncryptedType(String, flask_secret_key), default=None)
    passcode = Column(EncryptedType(String, flask_secret_key), default=None)
    spanish = Column(EncryptedType(Boolean, flask_secret_key), default=False)

    def __repr__(self):
        return '<Reminder %r, To: %r, From: %r>' % (self.id, self.to_phone, self.from_phone)

class Call(Base):
	"""A call coming in and any associated voicemail messages."""
	__tablename__ = 'call'

	id = Column(Integer, primary_key=True)
	call_sid = Column(EncryptedType(String, flask_secret_key))
	from_phone = Column(EncryptedType(String, flask_secret_key))
	time = Column(EncryptedType(String, flask_secret_key))
	message = Column(EncryptedType(String, flask_secret_key))
	spanish = Column(EncryptedType(Boolean, flask_secret_key), default=False)
	actions = Column(EncryptedType(String, flask_secret_key))
	assigned_to = Column(EncryptedType(String, flask_secret_key))

	def __repr__(self):
		return '<Call %r, From: %r, Time: %r, Message: %r>' % (self.id, self.from_phone, self.time, self.message)
