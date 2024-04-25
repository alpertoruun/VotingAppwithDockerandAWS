
from flask_mail import Message
from flask import current_app as app

def send_email(subject, recipient, body):
    mail = app.extensions.get('mail')
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.body = body
    mail.send(msg)
