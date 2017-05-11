from flask_wtf import FlaskForm
from wtforms import PasswordField, FileField, StringField, SelectField, SubmitField, IntegerField, TextAreaField
from wtforms.validators import DataRequired


markets = [
	('Indianapolis', 'Indianapolis'),
	('Columbus', 'Columbus'),
	('Bellevue', 'Bellevue'),
	('Seattle', 'Seattle'),
	('Denver/Boulder', 'Denver/Boulder'),
	('Chicago', 'Chicago'),
	('Minneapolis', 'Minneapolis')
]
markets.sort()

class RegisterForm(FlaskForm):
	first_name = StringField('first_name', validators = [DataRequired()])
	last_name = StringField('last_name', validators = [DataRequired()])
	email = StringField('email', validators = [DataRequired()])
	password = PasswordField('password', validators = [DataRequired()])
	register = SubmitField('Register')

class LoginForm(FlaskForm):
	email = StringField('email', validators = [DataRequired()])
	password = PasswordField('password', validators = [DataRequired()])
	login = SubmitField('Log in')

class NewMessageForm(FlaskForm):
	name = StringField('name', validators = [DataRequired()])
	message = StringField('message', validators = [DataRequired()])
	url = StringField('url')
	add_message = SubmitField('Submit')

class EditMessageForm(FlaskForm):
	id = SelectField('id', choices=[])
	name = StringField('name', validators = [DataRequired()])
	message = StringField('message', validators = [DataRequired()])
	url = StringField('url')
	edit = SubmitField('Edit')

class AddPhoneNumbersForm(FlaskForm):
	pasted_data = TextAreaField('data', validators = [DataRequired()])
	market = SelectField('Market', choices=markets)
	add_numbers = SubmitField('Upload Phone Numbers')

class UploadFileForm(FlaskForm):
	file = FileField()
	upload = SubmitField('Upload File')

class ExportCSVForm(FlaskForm):
	export = SubmitField('Export CSV')

class MakeCallForm(FlaskForm):
	market = SelectField('Market', choices=markets)
	message = SelectField('Message', choices=[])
	call = SubmitField('Call')

class MakeTextForm(FlaskForm):
	market = SelectField('Market', choices=markets)
	message = TextAreaField('Message', validators = [DataRequired()])
	text = SubmitField('Text')