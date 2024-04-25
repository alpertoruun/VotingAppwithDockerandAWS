# password_token_utils.py

import secrets
from flask import current_app
from datetime import datetime, timezone
from src import db
from src.accounts.models import PasswordResetToken
import pytz

def generate_reset_token():
    """Generate a secure random string for password reset token."""
    return secrets.token_urlsafe(16)  # 16 karakterlik güvenli bir token üretir

def create_password_reset_entry(user_id):
    """Create a password reset token entry in the database."""
    token = generate_reset_token()
    reset_entry = PasswordResetToken(
        user_id=user_id,
        token=token,
        created_at=datetime.now(timezone.utc),  # Zaman dilimi bilgisi ekleniyor
        used=False
    )
    db.session.add(reset_entry)
    db.session.commit()
    return token

def verify_reset_token(token):
    reset_entry = PasswordResetToken.query.filter_by(token=token).first()
    if not reset_entry or reset_entry.used:
        return None  
    
    utc_now = datetime.now(timezone.utc)
    utc_created_at = reset_entry.created_at.replace(tzinfo=timezone.utc) if reset_entry.created_at.tzinfo is None else reset_entry.created_at

    if (utc_now - utc_created_at).total_seconds() > 600:
        return None  
    return reset_entry.user_id
