from flask_mail import Message
from flask import current_app, url_for
from threading import Thread
from src.accounts.models import VoteToken, Voter
from src.utils.encrypt_election_id import encrypt_id
import logging

# E-posta gönderme fonksiyonu
def send_email(subject, recipient, body):
    mail = current_app.extensions.get('mail')
    msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.body = body
    mail.send(msg)

# Şifre sıfırlama e-postası
def send_reset_email(user, token):
    mail = current_app.extensions.get('mail')
    reset_url = url_for('accounts.reset_password', token=token, _external=True)
    msg = Message('Şifre Değiştirme İsteği', sender=current_app.config['MAIL_USERNAME'], recipients=[user.email])
    msg.body = f"Şifrenizi sıfırlamak için, aşağıdaki linke tıklayın:\n{reset_url}\nBu talepte bulunmadıysanız, bu e-postayı görmezden gelin."
    mail.send(msg)

# Oy kullanma bağlantısı içeren e-posta
def send_vote_link(voter, token, election):
    app = current_app._get_current_object()
    mail = app.extensions.get('mail')
    
    # Yüz doğrulama rotasına yönlendiren link
    face_control_link = url_for('core.face_control', token=token, _external=True)
    
    # E-posta mesajı
    msg = Message(
        f'{election.title} için Yüz Doğrulama Linkiniz', 
        sender=app.config['MAIL_USERNAME'], 
        recipients=[voter.email]
    )
    msg.body = (
        f"Sayın {voter.name.capitalize()} {voter.surname.capitalize()},\n\n"
        f"{election.title} seçimi için yüz doğrulamasından geçmeniz gerekmektedir. "
        f"Aşağıdaki linke tıklayarak yüz doğrulamanızı gerçekleştirin ve oy kullanma sayfasına yönlendirilin:\n{face_control_link}"
    )

    thread = Thread(target=send_async_email, args=(app, msg))
    thread.daemon = True
    thread.start()


# E-posta güncelleme e-postası
def send_update_email(new_mail, token):
    mail = current_app.extensions.get('mail')
    update_url = url_for('accounts.update_mail', token=token, _external=True)
    msg = Message('E-posta Adresinizi Güncelleyin', sender=current_app.config['MAIL_USERNAME'], recipients=[new_mail])
    msg.body = f"E-posta adresinizi güncellemek için lütfen aşağıdaki bağlantıya tıklayın:\n{update_url}\nEğer bu işlemi siz yapmadıysanız, bu e-postayı dikkate almayın."
    mail.send(msg)

# E-posta doğrulama e-postası
def send_verify_email(user, token):
    mail = current_app.extensions.get('mail')
    verify_url = url_for('accounts.verify_email', token=token, _external=True)
    msg = Message('E-posta Adresinizi Doğrulayın', sender=current_app.config['MAIL_USERNAME'], recipients=[user.email])
    msg.body = f"Yüz tanıma ile oylama sistemine kayıt olduğunuz için teşekkür ederiz! E-posta adresinizi doğrulamak için aşağıdaki bağlantıya tıklayın:\n{verify_url}\nEğer bu işlemi siz yapmadıysanız, lütfen bu e-postayı dikkate almayın."
    mail.send(msg)

# Seçim sonuçlarını içeren e-posta
def send_results_email(election):
    with current_app.app_context():  # Bu satırı ekleyin
        app = current_app._get_current_object()
        mail = app.extensions.get('mail')
        votetokens = VoteToken.query.filter_by(election_id=election.id).all()

        for token in votetokens:
            voter = Voter.query.get(token.voter_id)
            if voter:
                try:
                    encrypted_election_id = encrypt_id(token.election_id)
                    results_url = url_for('core.election_results', encrypted_election_id=encrypted_election_id, _external=True)

                    msg = Message(
                        f"{election.title} Sonuçları",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[voter.email]
                    )
                    msg.body = f"Merhaba {voter.name.capitalize()} {voter.surname.capitalize()},\n\n" \
                               f"{election.title} seçim sonuçları açıklandı. Aşağıdaki linke tıklayarak sonuçları görüntüleyebilirsiniz:\n{results_url}\n\n" \
                               "İyi günler dileriz!"
                    
                    thread = Thread(target=send_async_email, args=(app, msg))
                    thread.daemon = True
                    thread.start()

                except Exception as e:
                    logging.error(f"Sonuç e-postası {voter.email} adresine gönderilemedi: {str(e)}")


# Asenkron e-posta gönderme işlemi
def send_async_email(app, msg):
    with app.app_context():
        try:
            mail = app.extensions.get('mail')
            mail.send(msg)
            logging.info(f"E-posta {msg.recipients[0]} adresine başarıyla gönderildi.")
        except Exception as e:
            logging.error(f"E-posta gönderilemedi: {str(e)}")
