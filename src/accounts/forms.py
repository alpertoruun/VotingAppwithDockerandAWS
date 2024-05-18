from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField, validators
from wtforms.validators import DataRequired, Email, EqualTo, Length

from src.accounts.models import User


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Şifre", validators=[DataRequired(), Length(min=6, max=25, message="Şifreniz 6 ile 25 karakter arasında olmalıdır!")])


class RegisterForm(FlaskForm):
    email = EmailField(
        "Email", validators=[DataRequired(), Email(message="Geçersiz mail"), Length(min=6, max=40)]
    )
    password = PasswordField(
        "Şifre", validators=[DataRequired(), Length(min=6, max=25, message="Şifreniz 6 ile 25 karakter arasında olmalıdır!")]
    )
    confirm = PasswordField(
        "Yeni şifrenizi tekrarlayın",
        validators=[
            DataRequired(),
            EqualTo("password", message="Şifreler eşleşmiyor."),
        ],
    )

    def validate(self):
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append("Email zaten kayıtlı")
            return False
        return True
    
class RequestResetForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])


class PasswordChangeForm_(FlaskForm):
    password = PasswordField(
        "Şifre", validators=[DataRequired(), Length(min=6, max=25, message="Şifreniz 6 ile 25 karakter arasında olmalıdır!")]
    )
    confirm = PasswordField(
        "Yeni şifrenizi tekrarlayın",
        validators=[
            DataRequired(),
            EqualTo("password", message="Şifreler eşleşmiyor.")
        ],
    )


class EmailChangeForm(FlaskForm):
    email = EmailField('Yeni Mail Adresi', validators=[DataRequired(), Email()])


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Mevcut şifreniz', validators=[validators.DataRequired()])
    new_password = PasswordField('Yeni şifre', validators=[
        validators.DataRequired(),
        validators.Length(min=6, max=25, message="Şifreniz 6 ile 25 karakter arasında olmalıdır!")
    ])
    confirm_password = PasswordField(
        "Yeni şifrenizi tekrarlayın",
        validators=[
            validators.DataRequired(),
            validators.EqualTo('new_password', message="Şifreler eşleşmiyor.")
        ]
    )
    submit = SubmitField('Change Password')