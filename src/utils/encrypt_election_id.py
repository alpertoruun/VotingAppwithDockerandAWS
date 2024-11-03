from flask import current_app
import logging

def encrypt_id(token):
    fernet = current_app.extensions.get('fernet')
    encrypted_token = fernet.encrypt(str(token).encode()).decode()
    return encrypted_token

def decrypt_id(encrypted_token):
    fernet = current_app.extensions.get('fernet')
    try:
        decrypted_token = fernet.decrypt(encrypted_token.encode()).decode()
        return decrypted_token  # Bu aşamada string döndürüyoruz
    except Exception as e:
        logging.error(f"Token çözme hatası: {e}")
        return None
