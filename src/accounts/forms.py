from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField, validators
from wtforms.validators import DataRequired, Email, EqualTo, Length

from src.accounts.models import User


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    email = EmailField(
        "Email", validators=[DataRequired(), Email(message=None), Length(min=6, max=40)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=25)]
    )
    confirm = PasswordField(
        "Repeat password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )

    def validate(self):
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append("Email already registered")
            return False
        if self.password.data != self.confirm.data:
            self.password.errors.append("Passwords must match")
            return False
        return True
    
class RequestResetForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])


class PasswordChangeForm_(FlaskForm):
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=25)]
    )
    confirm = PasswordField(
        "Repeat Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match.")
        ],
    )


class EmailChangeForm(FlaskForm):
    email = EmailField('New Email', validators=[DataRequired(), Email()])


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[validators.DataRequired()])
    new_password = PasswordField('New Password', validators=[
        validators.DataRequired(),
        validators.Length(min=6, message='Your password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField(
        "Repeat Password",
        validators=[
            validators.DataRequired(),
            validators.EqualTo('new_password', message="Passwords must match.")
        ]
    )
    submit = SubmitField('Change Password')