from sqlalchemy import Column, Integer, String, Boolean
from ehhapp_twilio.database import Base

class User(Base):
    """A user capable of listening to voicemails"""
    __tablename__ = 'user'

    email = Column(String, primary_key=True)
    google_token = Column(String)
    authenticated = Column(Boolean, default=False)

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
    to_phone = Column(String)
    from_phone = Column(String)
    time = Column(String, default=None)
    delivered = Column(Boolean, default=False)
    freq = Column(Integer, default=24)
    message = Column(String, default=None)
    name = Column(String, default=None)
    passcode = Column(String, default=None)
    spanish = Column(Boolean, default=False)

    def __repr__(self):
        return '<Reminder %r, To: %r, From: %r>' % (self.id, self.to_phone, self.from_phone)

class Call(Base):
	"""A call coming in and any associated voicemail messages."""
	__tablename__ = 'call'

	id = Column(Integer, primary_key=True)
	call_sid = Column(String)
	from_phone = Column(String)
	time = Column(String)
	message = Column(String)
	spanish = Column(Boolean, default=False)
	actions = Column(String)
	assigned_to = Column(String)

	def __repr__(self):
		return '<Call %r, From: %r, Time: %r, Message: %r>' % (self.id, self.from_phone, self.time, self.message)
