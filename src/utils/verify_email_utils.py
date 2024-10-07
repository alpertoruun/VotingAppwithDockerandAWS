import secrets
from flask import current_app
from datetime import datetime, timezone
from src import db
from src.accounts.models import VerifyMailToken

def generate_email_verification_token():
    return secrets.token_urlsafe(16)

def create_email_verification_entry(user_id):
    token = generate_email_verification_token()
    verification_entry = VerifyMailToken(
        user_id=user_id,
        token=token,
        created_at=datetime.now(timezone.utc), 
        is_used=False
    )
    db.session.add(verification_entry)
    db.session.commit()
    return token

def verify_email_token(token):
    verification_entry = VerifyMailToken.query.filter_by(token=token).first()
    if not verification_entry or verification_entry.is_used:
        return None  
    
    utc_now = datetime.now(timezone.utc)
    utc_created_at = verification_entry.created_at.replace(tzinfo=timezone.utc) if verification_entry.created_at.tzinfo is None else verification_entry.created_at
    if (utc_now - utc_created_at).total_seconds() > 600:
        return None  
    return verification_entry.user_id 
