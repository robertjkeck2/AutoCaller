from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from response_app import application as app


db = SQLAlchemy(app)

class Users(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	first_name = db.Column(db.String(64))
	last_name = db.Column(db.String(64))
	email = db.Column(db.String(64), unique=True)
	pw_hash = db.Column(db.String(255))
	authenticated = db.Column(db.Boolean, default=False)	
	admin = db.Column(db.Boolean, default=False)

	def __init__(self, first_name, last_name, email, pw_hash):
		self.first_name = first_name
		self.last_name = last_name
		self.email = email
		self.pw_hash = generate_password_hash(pw_hash)

	def check_password(self, password):
		return check_password_hash(self.pw_hash, password)
	
	def is_active(self):
		return True

	def get_id(self):
		return self.id

	def is_authenticated(self):
		return self.authenticated

	def is_admin(self):
		return self.admin

	def is_anonymous(self):
		return False
	
	def __repr__(self):
		return '<User {}>'.format(self.email)

class Inbound(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))
	message = db.Column(db.String(255))
	url = db.Column(db.String(255))

	def __init__(self, name, message, url):
		self.name = name
		self.message = message
		self.url = url

	def __repr__(self):
		return "<{} Inbound Message>".format(self.name)
	
class Outbound(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))
	message = db.Column(db.String(255))
	url = db.Column(db.String(255))

	def __init__(self, name, message, url):
		self.name = name
		self.message = message
		self.url = url

	def __repr__(self):
		return "<{} Outbound Message>".format(self.name)

class Log(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	phone_number = db.Column(db.String(12), unique=True)
	market = db.Column(db.String(30))
	uploaded_by = db.Column(db.String(64))
	was_called = db.Column(db.Boolean)
	was_texted = db.Column(db.Boolean)
	called_timestamp = db.Column(db.DateTime)
	texted_timestamp = db.Column(db.DateTime)
	called_by = db.Column(db.String(64))
	texted_by = db.Column(db.String(64))
	
	def __init__(self, phone_number, market, uploaded_by, was_called, called_timestamp, called_by, was_texted, texted_timestamp, texted_by):
		self.phone_number = phone_number
		self.market = market
		self.uploaded_by = uploaded_by
		self.was_called = was_called
		self.called_timestamp = called_timestamp
		self.called_by = called_by
		self.was_texted = was_texted	
		self.texted_timestamp = texted_timestamp
		self.texted_by = texted_by

	def __repr__(self):
		return "<{} Log>".format(self.phone_number)

db.create_all()
db.session.commit()
