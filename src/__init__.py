from decouple import config
from flask import Flask, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_wtf import CSRFProtect
from cryptography.fernet import Fernet
from flask_apscheduler import APScheduler  # APScheduler import edildi

app = Flask(__name__)
app.config.from_object(config("APP_SETTINGS"))
mail = Mail(app)

app.config['SERVER_NAME'] = config('SERVER_NAME')
app.config['PREFERRED_URL_SCHEME'] = config('PREFERRED_URL_SCHEME')

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
scheduler = APScheduler()

# Zamanlanmış görev: 60 saniyede bir çalışacak
@scheduler.task('interval', id='count_votes_job', seconds=60)
def scheduled_count_votes():
    with scheduler.app.app_context():
        from src.utils.count_votes_utils import count_votes
        count_votes()

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
