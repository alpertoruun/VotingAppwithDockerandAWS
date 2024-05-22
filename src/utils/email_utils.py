from flask_mail import Message
from flask import current_app, url_for
from threading import Thread
import logging



def send_email(subject, recipient, body):
    mail = current_app.extensions.get('mail')
    msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.body = body
    mail.send(msg)

def send_reset_email(user, token):
    mail = current_app.extensions.get('mail')
    msg = Message('Şifre Değiştirme İsteği', sender=current_app.config['MAIL_USERNAME'], recipients=[user.email])
    reset_url = url_for('accounts.reset_password', token=token, _external=True)
    msg.body = f"""Şifrenizi sıfırlamak için, alttaki linke tıklayınız:
{reset_url}

Bu talepte bulunmadıysanız, bu e-postayı görmezden gelin. Hiçbir değişiklik yapılmayacaktır"""
    mail.send(msg)


def send_vote_link(user, token, election):
    app = current_app._get_current_object()
    mail = app.extensions.get('mail')
    msg = Message(f'{election.title} için Oy Kullanma Linkiniz',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.email])
    link = url_for('core.vote', token=token, _external=True)
    msg.body = f'Sayın {user.name.capitalize()} {user.surname.capitalize()},\n{election.title} seçimi için {election.start_date.strftime("%d-%m-%Y %H:%M")} tarihinden {election.end_date.strftime("%d-%m-%Y %H:%M")} tarihine kadar oy kullanabilirsiniz.\nOy kullanmak için aşağıdaki linke tıklayınız:\n{link}'
    
    thread = Thread(target=send_async_email, args=(app, msg))
    thread.daemon = True
    thread.start()

def send_async_email(app, msg):
    with app.app_context():
        mail = app.extensions.get('mail')
        try:
            mail.send(msg)
            logging.info("Mail sent successfully to %s", msg.recipients)
        except Exception as e:
            logging.error("Failed to send mail to %s: %s", msg.recipients, str(e))


def send_update_email(new_mail, token):
    mail = current_app.extensions.get('mail')
    msg = Message('Email Adresinizi Güncelleyin', sender=current_app.config['MAIL_USERNAME'], recipients=[new_mail])
    update_url = url_for('accounts.update_mail', token=token, _external=True)
    msg.body = f"E-posta adresinizi güncellemek için lütfen aşağıdaki bağlantıyı ziyaret edin:\n{update_url}\n\nBu e-posta değişikliğini talep etmediyseniz, lütfen bu e-postayı dikkate almayın ve hiçbir değişiklik yapılmayacaktır."

    mail.send(msg)