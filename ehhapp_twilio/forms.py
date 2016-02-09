from wtforms import Form, TextField, validators
import re

def filter_phone(value):
	if value == None:
		return None
	sanitize = re.compile(r'[^\d]+')
	return str(sanitize.sub('', value))

class IntentForm(Form):
    digit = TextField('Digit', [validators.Length(min=1, max=1)])
    description = TextField('Description', [validators.Length(min=6, max=200)])
    required_recipients = TextField('Required recipients')
    distributed_recipients = TextField('Assign from schedule')

class AssignmentForm(Form):
   from_phone = TextField('From phone', validators=[validators.Length(min=10, max=10)],
					filters=[lambda x: x, filter_phone])
   recipients = TextField('Assigned to')

