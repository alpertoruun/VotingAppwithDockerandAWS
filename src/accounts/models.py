from datetime import datetime, timezone

from flask_login import UserMixin

from src import bcrypt, db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_mail_approved = db.Column(db.Boolean, nullable=False, default=False)
    is_face_approved = db.Column(db.Boolean, nullable=False, default=False)
    tc = db.Column(db.String(11), unique=True, nullable=True)
    name = db.Column(db.String(50), nullable=True)
    surname = db.Column(db.String(50), nullable=True)
    face_id = db.Column(db.Integer, db.ForeignKey('face_recognition.id'), nullable=True)

    face_recognition = db.relationship(
        'FaceRecognition',
        backref=db.backref('user', lazy=True),
        foreign_keys=[face_id]
    )

    def __init__(self, email, password, tc=None, name=None, surname=None, face_id=None, is_admin=False, is_mail_approved=False, is_face_approved=False):
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.created_on = datetime.now()
        self.tc = tc
        self.name = name
        self.surname = surname
        self.face_id = face_id
        self.is_admin = is_admin
        self.is_mail_approved = is_mail_approved
        self.is_face_approved = is_face_approved

    def __repr__(self):
        return f"<User {self.email}>"


class FaceRecognition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encoding = db.Column(db.LargeBinary, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)


class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    is_counted = db.Column(db.Boolean, nullable=False, default=False) 
    participation_rate = db.Column(db.Float, default=0.0, nullable=False)  



class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    votes = db.relationship('Votes', backref='option', lazy=True)

class Votes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class OptionCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)
    vote_count = db.Column(db.Integer, default=0)

class VoteToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(256), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    election = db.relationship('Election', backref=db.backref('tokens', lazy=True))

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(256), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    used = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy=True))

class UpdateEmailToken(db.Model):
    __tablename__ = 'update_email_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    new_mail = db.Column(db.String(255), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', backref=db.backref('update_email_tokens', lazy=True))

    def __repr__(self):
        return f'<UpdateEmailToken {self.token}>'


class VerifyMailToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(256), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    
    user = db.relationship('User', backref=db.backref('verify_mail_tokens', lazy=True))

    def __repr__(self):
        return f'<VerifyMailToken {self.token}>'