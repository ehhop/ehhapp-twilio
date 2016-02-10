from wtforms import Form, TextField, validators
import re

def filter_phone(value):			# remove other characters except for digits
	if value == None:
		return None
	sanitize = re.compile(r'[^\d]+')
	return str(sanitize.sub('', value))

class IntentForm(Form):				
    '''GUI: routing form used in views'''
    digit = TextField('Digit', [validators.Length(min=1, max=1)])
    description = TextField('Description', [validators.Length(min=6, max=200)])
    required_recipients = TextField('Required recipients')
    distributed_recipients = TextField('Assign from schedule')

class AssignmentForm(Form):
   '''GUI: assignment form used in views'''
   from_phone = TextField('From phone', validators=[validators.Length(min=10, max=10)],
					filters=[lambda x: x, filter_phone])
   recipients = TextField('Assigned to')

