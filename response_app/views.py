from collections import OrderedDict
import os
import pandas as pd
import csv
from datetime import datetime

from flask import request, render_template, redirect, send_file, flash, abort, jsonify, url_for, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from flask_admin import BaseView, expose
from flask_admin.contrib.sqla import ModelView
from twilio import twiml
from twilio.rest import TwilioRestClient

from response_app import application as app
from response_app import csrf, lm, admin, celery
from response_app.config import ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER
from response_app.models import Users, Inbound, Outbound, Log, db
from response_app.forms import RegisterForm, LoginForm, NewMessageForm, EditMessageForm, AddPhoneNumbersForm, UploadFileForm, ExportCSVForm, MakeCallForm, MakeTextForm

client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
hostname = 'hostname'

@celery.task
def calling(message_url, market, email, ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER):
    with app.app_context():
        client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
        phone_numbers = Log.query.filter_by(market=market).all()
        for phone in phone_numbers:
            if not phone.was_called:
                call = client.calls.create(to=phone.phone_number,
                       from_=TWILIO_NUMBER,
                       url=message_url,
                       if_machine='Continue')
                phone.was_called = True
                phone.called_timestamp = datetime.now()
                phone.called_by = email
                db.session.commit()

@celery.task
def texting(message, market, email, ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER):
    with app.app_context():
        client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
        phone_numbers = Log.query.filter_by(market=market).all()
        for phone in phone_numbers:
            if not phone.was_texted:
                call = client.messages.create(to=phone.phone_number,
                       from_=TWILIO_NUMBER,
                       body=message)
                phone.was_texted = True
                phone.texted_timestamp = datetime.now()
                phone.texted_by = email
                db.session.commit()

@lm.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

@app.route('/', methods=['GET'])
def index():
    if current_user:
        if current_user.is_authenticated:
            return redirect(url_for('home'))
    return render_template('index.html')    

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            first_name = form.first_name.data
            last_name = form.last_name.data
            email = form.email.data
            password = form.password.data
            end_slug = str(email)[-13:]
            if end_slug == '@testemail.com':
                new_user = Users(first_name, last_name, email, password)
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login'))
        else:
            flash('Invalid email address. Please try again')
        return redirect(url_for('register'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = Users.query.filter_by(email=email).first()
        if not user:
            flash('Incorrect email/password. Please try again.')
            return redirect(url_for('login'))
        if user.check_password(password):
            user.authenticated = True
            db.session.commit()
            login_user(user, remember=True)
            flash('Logged in successfully')
            next = request.args.get('next')
            return redirect(next or url_for('home'))
        else:
            flash('Incorrect email/password. Please try again.')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route('/logout', methods=['GET','POST'])
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/call', methods=['GET','POST'])
@login_required
def call():
    choices = [(str(outbound.id), outbound.name) for outbound in Outbound.query.all()]
    form = MakeCallForm()
    form.message.choices = choices
    if request.method == 'POST':
        if form.validate_on_submit() and form.market.data and form.message.data:
            market = form.market.data
            message_id = form.message.data
            message_url = "{0}{1}".format(hostname, url_for('outbound_twilio', message_id=message_id))
            calling.delay(message_url, market, current_user.email, ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER)
            flash('Calling...  Please refresh to see call progress.')
            return redirect(url_for('log'))
        else:
            flash('No message selected. Please add an outbound message.')
            return redirect(url_for('outbound'))
    elif request.method == 'GET':
        return render_template('call.html',
            form=form)
    else:
        abort(405)

@app.route('/text', methods=['GET','POST'])
@login_required
def text():
    form = MakeTextForm()
    if request.method == 'POST':  
        if form.validate_on_submit() and form.market.data and form.message.data:
            market = form.market.data
            message = form.message.data
            texting.delay(message, market, current_user.email, ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER)
            flash('Texting...  Please refresh to see text progress.')
            return redirect(url_for('log'))
        else:
            flash('No message written. Please write a text message.')
            return redirect(url_for('text'))
    elif request.method == 'GET':
        return render_template('text.html',
            form=form)
    else:
        abort(405)

@app.route('/outbound', methods=['GET','POST'])
@login_required
def outbound():
    choices = [(str(outbound.id), outbound.name) for outbound in Outbound.query.all()]
    new_message_form = NewMessageForm()
    edit_message_form = EditMessageForm()
    edit_message_form.id.choices = choices
    if request.method == 'GET':
        return _get_messages(model='outbound',
            html_file='outbound.html',
            new_message_form=new_message_form,
            edit_message_form=edit_message_form)
    elif request.method == 'POST':
        return _post_messages(model='outbound',
            new_message_form=new_message_form,
            edit_message_form=edit_message_form)
    else:
        abort(405)

@app.route('/outbound/<message_id>', methods=['POST'])
@csrf.exempt
def outbound_twilio(message_id):
    if request.method == 'POST':
        outbound_message = Outbound.query.filter_by(id=message_id).first()
        message = outbound_message.message  
        url = outbound_message.url
        return _return_message(message, url=url)
    else:
        abort(405)

@app.route('/inbound', methods=['GET','POST'])
@login_required
def inbound():
    choices = [(str(inbound.id), inbound.name) for inbound in Inbound.query.all()]
    new_message_form = NewMessageForm()
    edit_message_form = EditMessageForm()
    edit_message_form.id.choices = choices
    if request.method == 'GET':
        return _get_messages(model='inbound',
            html_file='inbound.html',
            new_message_form=new_message_form,
            edit_message_form=edit_message_form)
    elif request.method == 'POST':
        return _post_messages(model='inbound',
            new_message_form=new_message_form,
            edit_message_form=edit_message_form)
    else:
        abort(405)

@app.route('/inbound/<message_id>', methods=['POST'])
@csrf.exempt
def inbound_twilio(message_id):
    if request.method == 'POST':
        inbound_message = Inbound.query.filter_by(id=message_id).first()
        message = inbound_message.message
        url = inbound_message.url
        return _return_message(message, url=url)
    else:
        abort(405)

@app.route('/audio', methods=['GET','POST'])
@login_required
def audio():
    form = UploadFileForm()
    if request.method == 'POST':
        if form.validate_on_submit() and form.file.data:
            file = form.file.data
            if file and _allowed_audio(file.filename):
                filename = file.filename
                file.save(os.path.join(app.config['AUDIO_FOLDER'], filename))
                flash('Audio file successfully uploaded.')
                return redirect(url_for('audio'))
            else:
                flash('Incorrect file type. Please try again')
                return redirect(url_for('audio'))
    files = os.listdir(app.config['AUDIO_FOLDER'])
    return render_template('audio.html', form=form, files=files)

@app.route('/play/<filename>', methods=['GET','POST'])
def play(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)

@app.route('/log', methods=['GET','POST'])
@app.route('/log/<phone_number>', methods=['GET','POST'])
@login_required
def log(phone_number=None):
    form = ExportCSVForm()
    if not phone_number:
        if request.method == 'GET':
            phone_numbers = Log.query.all()
            if not phone_numbers:
                return render_template("log.html", 
                    form=form,
                    phone_numbers=[])
            else:
                all_numbers = []
                for numbers in phone_numbers:
                    res = OrderedDict()
                    res['phone_number'] = numbers.phone_number
                    res['market'] = numbers.market
                    res['uploaded_by'] = numbers.uploaded_by
                    res['was_called'] = numbers.was_called
                    res['called_timestamp'] = numbers.called_timestamp
                    res['called_by'] = numbers.called_by
                    res['was_texted'] = numbers.was_texted
                    res['texted_timestamp'] = numbers.texted_timestamp
                    res['texted_by'] = numbers.texted_by
                    all_numbers.append(res)
                return render_template("log.html",
                    form=form,
                    phone_numbers=all_numbers)
        elif request.method == 'POST':
            if form.validate_on_submit() and form.export.data:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'call_log.csv')
                with open(filepath, 'wb') as f:
                    outcsv = csv.writer(f)
                    outcsv.writerow(['phone_number', 'was_called'])
                    call_log = Log.query.all()
                    for phone in call_log:
                        outcsv.writerow([phone.phone_number, phone.was_called])
                return send_file(filepath,
                    mimetype='text/csv',
                    attachment_filename='call_log.csv',
                    as_attachment=True)
        else:
            abort(405)
    else:
        formatted_number = "+{}".format(str(phone_number))
        phone_info = Log.query.filter_by(phone_number=formatted_number).first()
        return render_template("log.html",
        form=form,
            phone_numbers=phone_info)
    
@app.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    form = AddPhoneNumbersForm()
    upload_form = UploadFileForm()
    if request.method == 'POST':
        if form.validate_on_submit() and form.pasted_data.data:
            data = form.pasted_data.data
            phone_numbers = data.split('\n')
            for phone in phone_numbers:
                phone = phone.strip()
                if _validate_phone_number(str(phone)):
                    phone_number="+{}".format(str(phone).strip(' '))
                    if Log.query.filter_by(phone_number=phone_number).first() is None:
                        market = form.market.data
                        was_called = False
                        was_texted = False
                        called_timestamp = None
                        texted_timestamp = None
                        uploaded_by = current_user.email
                        called_by = None
                        texted_by = None
                        new_log = Log(phone_number, market, uploaded_by, was_called, called_timestamp, called_by, was_texted, texted_timestamp, texted_by)
                        db.session.add(new_log)
                    db.session.commit()             
            flash('Data Successfully Uploaded')
            return redirect(url_for('log'))
        elif upload_form.validate_on_submit() and upload_form.file.data:
            file = upload_form.file.data
            if file and _allowed_file(file.filename):
                filename = file.filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                csv_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            else:
                flash('Incorrect file type. Please try again')
                return redirect(url_for('upload'))
            df = pd.read_csv(csv_file, header=0, names=['phone_number','market'])
            for i in range(0,len(df)):
                if _validate_phone_number(str(df['phone_number'].iloc[i])):
                    phone_number = "+{}".format(str(df['phone_number'].iloc[i]))
                    if Log.query.filter_by(phone_number=phone_number).first() is None:
                        market = str(df['market'].iloc[i])
                        was_called = False
                        was_texted = False
                        called_timestamp = None
                        texted_timestamp = None
                        uploaded_by = current_user.email
                        called_by = None
                        texted_by = None
                        new_log = Log(phone_number, market, uploaded_by, was_called, called_timestamp, called_by, was_texted, texted_timestamp, texted_by)
                        db.session.add(new_log)
                    db.session.commit()
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('Data Successfully Uploaded')
            return redirect(url_for('log'))
    return render_template("upload.html",
        form=form,
        upload_form=upload_form)

class UserView(ModelView):
    
    def is_accessible(self):
        return current_user.is_admin()

admin.add_view(UserView(Users, db.session))
admin.add_view(UserView(Inbound, db.session))
admin.add_view(UserView(Outbound, db.session))
admin.add_view(UserView(Log, db.session))

#Private helper methods
def _return_message(message, url=None):
    resp = twiml.Response()
    if url:
        resp.play(url)
    else:
        resp.say(message)
    return str(resp)     

def _format_message(msg):
    res = OrderedDict()
    res['id'] = msg.id
    res['name'] = msg.name
    res['message'] = msg.message
    res['url'] = msg.url
    return res

def _allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in set(['csv'])

def _allowed_audio(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in set(['wav','mp3'])

def _validate_phone_number(phone_number):
    if phone_number[0] == '1':
        if len(phone_number) == 11:
            return True
    else:
        return False

def _get_messages(model, html_file, new_message_form, edit_message_form):
    if model == 'outbound':
        messages = Outbound.query.all()
    elif model == 'inbound':
        messages = Inbound.query.all()
    if not messages:
        return render_template(html_file,
                    form=new_message_form,
                    edit_form=edit_message_form,
                    all_messages=[])
    all_messages = []
    for msg in messages:
        res = _format_message(msg)
        all_messages.append(res)
    return render_template(html_file,
                form=new_message_form,
                edit_form=edit_message_form,
                all_messages=all_messages)

def _post_messages(model, new_message_form, edit_message_form):
    if new_message_form.validate_on_submit() and new_message_form.add_message.data:
        name = new_message_form.name.data
        message = new_message_form.message.data
        url = new_message_form.url.data
        if model == 'outbound':
            added_message = Outbound(name, message, url)
        elif model == 'inbound': 
            added_message = Inbound(name, message, url)
        else:
            abort(404)
        db.session.add(added_message)
        db.session.commit()
        return redirect(url_for(model))
    elif edit_message_form.validate_on_submit() and edit_message_form.edit.data:
        if model == 'outbound':
            edited_message = Outbound.query.filter_by(id=edit_message_form.id.data).first()
        elif model == 'inbound':
            edited_message = Inbound.query.filter_by(id=edit_message_form.id.data).first()
        else:
            abort(404)
        if edited_message:
            edited_message.name = edit_message_form.name.data
            edited_message.message = edit_message_form.message.data
            edited_message.url = edit_message_form.url.data
            db.session.commit()
            return redirect(url_for('{}'.format(model)))
        else:
            flash('Message ID not found.  Please try again.')
            return redirect(url_for(model))
    else:
        return redirect(url_for(model))
