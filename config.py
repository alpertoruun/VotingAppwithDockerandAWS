from decouple import config

DATABASE_URI = config("DATABASE_URL")
if DATABASE_URI.startswith("postgres://"):
    DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql://", 1)


class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = config("SECRET_KEY", default="guess-me")
    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BCRYPT_LOG_ROUNDS = 13
    WTF_CSRF_ENABLED = True
    DEBUG_TB_ENABLED = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    FERNET_KEY = config("FERNET_KEY", default="guess-me")
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC"
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,
        'max_instances': 1,
        'misfire_grace_time': 300
    }
    SERVER_NAME = config('SERVER_NAME', default='localhost:5000')
    PREFERRED_URL_SCHEME = config('PREFERRED_URL_SCHEME', default='http')
    APPLICATION_ROOT = '/'


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    DEBUG_TB_ENABLED = True
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'alpertorun4455@gmail.com'
    MAIL_PASSWORD = 'ydpj xeht iwrr raip'


