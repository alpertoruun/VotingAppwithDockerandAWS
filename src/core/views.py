from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.accounts.models import db, Election, Voter, Option



core_bp = Blueprint("core", __name__)


@core_bp.route("/create_election", methods=['GET', 'POST'])
@login_required
def create_election():
    if not current_user.is_authenticated:
        flash('Giriş yapmalısınız!')
        return redirect(url_for('login'))
    if request.method == 'POST':

        title = request.form.get('title')
        description = request.form.get('description')
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        options = request.form.getlist('options')  
        voter_tcs = request.form.getlist('voterTc[]')
        voter_names = request.form.getlist('voterName[]')
        voter_surnames = request.form.getlist('voterSurname[]')
        voter_emails = request.form.getlist('voterEmail[]')
        election = Election(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            creator_id=current_user.id
        )
        db.session.add(election)
        db.session.commit()

        for option_desc in options:
            option = Option(description=option_desc, election_id=election.id)
            db.session.add(option)
        
        for tc, name, surname, email in zip(voter_tcs, voter_names, voter_surnames, voter_emails):
            voter = Voter(tc=tc, name=name, surname=surname, email=email)
            db.session.add(voter)

        db.session.commit() 

        flash('Oylama başarıyla oluşturuldu!')
        
    return render_template("core/index.html")
