# update_email_token_utils.py

import secrets
from flask import current_app
from datetime import datetime, timezone
from src import db
from src.accounts.models import UpdateEmailToken, User

def generate_update_token():
    """Generate a secure random string for email update token."""
    return secrets.token_urlsafe(16)  # 16 karakterlik güvenli bir token üretir

def create_update_email_entry(user_id, new_mail):
    """Create an email update token entry in the database."""
    token = generate_update_token()
    update_entry = UpdateEmailToken(
        user_id=user_id,
        new_mail=new_mail,
        token=token,
        created_at=datetime.now(timezone.utc),  # Zaman dilimi bilgisi ekleniyor
        used=False
    )
    db.session.add(update_entry)
    db.session.commit()
    return token

def verify_update_token(token):
    update_entry = UpdateEmailToken.query.filter_by(token=token).first()
    if not update_entry or update_entry.used:
        return None, None  

    utc_now = datetime.now(timezone.utc)
    utc_created_at = update_entry.created_at.astimezone(timezone.utc)
    if (utc_now - utc_created_at).total_seconds() > 600:  
        return None, None

    return update_entry.user_id, update_entry.new_mail