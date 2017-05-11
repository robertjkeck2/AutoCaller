from flask import Flask 
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_admin import Admin

from celery import Celery


application = Flask(__name__)
csrf = CSRFProtect(application)
lm = LoginManager()
lm.init_app(application)
admin = Admin()
admin.init_app(application)
application.config['SQLALCHEMY_DATABASE_URI'] = 'path/to/db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.config['UPLOAD_FOLDER'] = 'path/to/uploads/folder'
application.config['AUDIO_FOLDER'] = '/path/to/audio/folder'
application.config['CELERY_BROKER_URL'] = 'path/to/celery/broker'
application.config['CELERY_RESULT_BACKEND'] = 'path/to/celery/broker'
application.secret_key = 'secret_key'

celery = Celery(application.name, broker=application.config['CELERY_BROKER_URL'])
celery.conf.update(application.config)

import response_app.views

if __name__ == "__main__":
    app.run(host='0.0.0.0')