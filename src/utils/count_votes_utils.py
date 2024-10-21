from datetime import datetime, timezone
from flask_mail import Message
from flask import current_app, url_for
from threading import Thread
from src.accounts.models import db,VoteToken, Voter, OptionCount, Election, Votes, Option
import logging
from datetime import datetime, timezone
from src.utils.email_utils import send_results_email


def count_votes():
    elections = Election.query.filter(Election.end_date < datetime.now(timezone.utc), Election.is_counted == False).all()

    for election in elections:
        print(f"Seçim ID {election.id} için oylar sayılıyor...")
        election.is_counted = True
        total_tokens = VoteToken.query.filter_by(election_id=election.id).count()  
        votes_cast = Votes.query.filter_by(election_id=election.id).count()  

        if total_tokens > 0:
            participation_rate = (votes_cast / total_tokens) * 100
        else:
            participation_rate = 0.0

        options = Option.query.filter_by(election_id=election.id).all()
        for option in options:
            vote_count = Votes.query.filter_by(option_id=option.id, election_id=election.id).count()
            option_count_entry = OptionCount(
                election_id=election.id,
                option_id=option.id,
                vote_count=vote_count
            )
            db.session.add(option_count_entry)
        
        election.participation_rate = participation_rate
        db.session.commit()
        send_results_email(election)
