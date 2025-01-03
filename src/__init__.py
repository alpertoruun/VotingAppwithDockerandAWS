from decouple import config
from flask import Flask, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_wtf import CSRFProtect
from cryptography.fernet import Fernet
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from src.utils.encrypt_election_id import encrypt_id, decrypt_id

app = Flask(__name__, static_folder="static")
app.jinja_env.globals.update(encrypt_id=encrypt_id, decrypt_id=decrypt_id)
app.config.from_object(config("APP_SETTINGS"))
mail = Mail(app)

app.config['PREFERRED_URL_SCHEME'] = config('PREFERRED_URL_SCHEME')
app.config['SERVER_NAME'] = config('SERVER_NAME')

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_message = "Bu sayfaya erişmek için lütfen oturum açın."
login_manager.login_message_category = "warning"

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

fernet_key = config('FERNET_KEY')
app.extensions['fernet'] = Fernet(fernet_key)

csrf = CSRFProtect(app)

# Registering blueprints
from src.accounts.views import accounts_bp
from src.core.views import core_bp

app.register_blueprint(accounts_bp)
app.register_blueprint(core_bp)

from src.accounts.models import User

login_manager.login_view = "accounts.login"
login_manager.login_message_category = "danger"

# Zamanlanmış Görev için APScheduler başlatıldı
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
file_handler = logging.FileHandler('/opt/votingapp/logs/gunicorn.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)
app.logger.addHandler(file_handler)

scheduler_logger = logging.getLogger('apscheduler')
scheduler_logger.setLevel(logging.DEBUG)
scheduler_logger.addHandler(file_handler)

scheduler = APScheduler(scheduler=BackgroundScheduler(daemon=True))

scheduler.add_jobstore('memory')
scheduler_logger.info("Scheduler initialized")

@scheduler.task('interval', id='count_votes_job', seconds=60)
def scheduled_count_votes():
    with app.app_context():
        try:
            from src.utils.count_votes_utils import count_votes
            app.logger.info("Counting votes started...")
            count_votes()
            app.logger.info("Counting votes completed successfully")
        except Exception as e:
            app.logger.error(f"Error in count_votes: {str(e)}")

scheduler.init_app(app)
scheduler.start()

@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.id == int(user_id)).first()

#### error handlers

@app.errorhandler(401)
def unauthorized_page(error):
    return render_template("errors/401.html"), 401


@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error_page(error):
    return render_template("errors/500.html"), 500
