from flask_mail import Message
from flask import current_app, url_for
from threading import Thread
from src.accounts.models import VoteToken, Voter
from src.utils.encrypt_election_id import encrypt_id  # encrypt_id'yi içe aktarıyoruz
import logging


def send_results_email(election):
    app = current_app._get_current_object()  # Uygulama nesnesini alıyoruz
    mail = app.extensions.get('mail')
    votetokens = VoteToken.query.filter_by(election_id=election.id).all()

    for token in votetokens:
        voter = Voter.query.get(token.voter_id)
        if voter:
            try:
                msg = Message(f"{election.title} Sonuçları",
                              sender=app.config['MAIL_USERNAME'],
                              recipients=[voter.email])
                
                # Election ID'yi şifreleyerek kullanıyoruz
                encrypted_election_id = encrypt_id(token.election_id)
                
                # Uygulama bağlamı dışında URL oluşturulamaz, o yüzden burada manuel URL oluşturuyoruz
                server_name = app.config.get("SERVER_NAME", "localhost:5000")  # Varsayılan olarak localhost:5000 kullanılıyor
                results_url = f"http://localhost:5000/election/{encrypted_election_id}"
                
                msg.body = f"Merhaba {voter.name.capitalize()} {voter.surname.capitalize()},\n\n" \
                           f"{election.title} seçim sonuçları açıklandı. " \
                           f"Aşağıdaki linke tıklayarak sonuçları görüntüleyebilirsiniz:\n{results_url}\n\n" \
                           "İyi günler dileriz!"
                
                # E-postayı async olarak göndermek için thread kullanıyoruz
                thread = Thread(target=send_async_email, args=(app, msg))
                thread.daemon = True
                thread.start()

            except Exception as e:
                logging.error(f"Sonuç e-postası {voter.email} adresine gönderilemedi: {str(e)}")


def send_async_email(app, msg):
    # Uygulama bağlamını manuel olarak başlatıyoruz
    with app.app_context():
        try:
            mail = app.extensions.get('mail')
            mail.send(msg)
            logging.info(f"Sonuç e-postası {msg.recipients[0]} adresine başarıyla gönderildi.")
        except Exception as e:
            logging.error(f"E-posta gönderilemedi: {str(e)}")
