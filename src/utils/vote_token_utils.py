import secrets
from src import db
from src.accounts.models import VoteToken

def generate_vote_token():
    """Generate a secure random string for voting."""
    return secrets.token_urlsafe(16)

def create_vote_token_entry(voter_id, election_id):
    """Create a voting token entry in the database."""
    token = generate_vote_token()
    vote_token_entry = VoteToken(
        voter_id=voter_id,
        election_id=election_id,
        token=token,
        used=False
    )
    db.session.add(vote_token_entry)
    db.session.commit()
    return token
