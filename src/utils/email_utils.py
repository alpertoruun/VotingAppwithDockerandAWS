from flask_mail import Message
from flask import current_app as app, url_for

def send_email(subject, recipient, body):
    mail = app.extensions.get('mail')
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.body = body
    mail.send(msg)

def send_reset_email(user, token):
    mail = app.extensions.get('mail')
    msg = Message('Password Reset Request', sender=app.config['MAIL_USERNAME'], recipients=[user.email])
    reset_url = url_for('accounts.reset_password', token=token, _external=True)
    msg.body = f"""To reset your password, visit the following link:
{reset_url}

If you did not make this request then simply ignore this email and no changes will be made."""
    mail.send(msg)
