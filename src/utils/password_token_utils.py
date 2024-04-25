# password_token_utils.py

import secrets
from flask import current_app
from datetime import datetime, timezone
from src import db
from src.accounts.models import PasswordResetToken

def generate_reset_token():
    """Generate a secure random string for password reset token."""
    return secrets.token_urlsafe(16)  # 16 karakterlik güvenli bir token üretir

def create_password_reset_entry(user_id):
    """Create a password reset token entry in the database."""
    token = generate_reset_token()
    reset_entry = PasswordResetToken(
        user_id=user_id,
        token=token,
        created_at=datetime.now(timezone.utc),
        used=False
    )
    db.session.add(reset_entry)
    db.session.commit()
    return token

def verify_reset_token(token):
    """Verify the password reset token and return the user ID if valid."""
    reset_entry = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if reset_entry and (datetime.now(timezone.utc) - reset_entry.created_at).total_seconds() < 600:
        reset_entry.used = True
        db.session.commit()
        return reset_entry.user_id
    return None
