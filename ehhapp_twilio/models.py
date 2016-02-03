from sqlalchemy import Column, Integer, String, Boolean
from ehhapp_twilio.database import Base

class User(Base):
    """An admin user capable of viewing reports.

    :param str email: email address of user
    :param str google_token: callback token

    """
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
    """An admin user capable of viewing reports.
    :param str email: email address of user
    :param str google_token: callback token
    """
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
