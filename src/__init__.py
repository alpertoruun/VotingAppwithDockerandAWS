from decouple import config
from flask import Flask, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_wtf import CSRFProtect
from cryptography.fernet import Fernet
import logging
from src.utils.encrypt_election_id import encrypt_id, decrypt_id

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
app = Flask(__name__, static_folder="static")
app.jinja_env.globals.update(encrypt_id=encrypt_id, decrypt_id=decrypt_id)
app.config.from_object(config("APP_SETTINGS"))
mail = Mail(app)

app.config['PREFERRED_URL_SCHEME'] = config('PREFERRED_URL_SCHEME')

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.INFO)


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
