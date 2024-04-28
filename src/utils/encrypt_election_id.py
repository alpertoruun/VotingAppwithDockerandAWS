from flask import current_app

def encrypt_id(election_id):
    fernet = current_app.extensions.get('fernet')
    return fernet.encrypt(str(election_id).encode()).decode()

def decrypt_id(token):
    fernet = current_app.extensions.get('fernet')
    try:
        return int(fernet.decrypt(token.encode()).decode())
    except Exception as e:
        return None
