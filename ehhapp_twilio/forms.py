from wtforms import Form, TextField, validators, FileField
import re

class DisabledTextField(TextField):
  def __call__(self, *args, **kwargs):
    kwargs.setdefault('disabled', True)
    return super(DisabledTextField, self).__call__(*args, **kwargs)

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

class AudiofileForm(Form):
	'''GUI: edit audio files for IVR menu'''
	audio_file = FileField('Upload new audio')
	audio_file_name = TextField("Audio file name")
