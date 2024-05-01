from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from src.accounts.models import db, Election, Voter, Option, Votes, VoteToken
from src.utils.email_utils import send_vote_link
from src.utils.email_validator import validate_email_address
from src.utils.vote_token_utils import create_vote_token_entry
from src.utils.encrypt_election_id import encrypt_id, decrypt_id


core_bp = Blueprint("core", __name__)

@core_bp.route('/my_elections')
@login_required
def my_elections():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    elections_query = Election.query.filter_by(creator_id=current_user.id)
    elections = elections_query.paginate(page=page, per_page=per_page, error_out=True)
    for election in elections.items:
        election.encrypted_id = encrypt_id(election.id)
    return render_template('core/my_elections.html', elections=elections)


@core_bp.route('/election/<encrypted_election_id>')
def election_results(encrypted_election_id):
    election_id = decrypt_id(encrypted_election_id)
    if election_id is None:
        abort(404)  # Geçersiz veya zaman aşımına uğramış şifreli ID
    
    election = Election.query.get(election_id)
    if not election:
        abort(404)  # Election bulunamadı

    options = Option.query.filter_by(election_id=election.id).all()
    votes = Votes.query.filter_by(election_id=election.id).all()
    total_tokens = VoteToken.query.filter_by(election_id=election.id).count()

    # Oylama sonuçlarını ve katılım oranını hesapla
    results = {option.description: 0 for option in options}
    for vote in votes:
        results[vote.option.description] += 1
    
    # Katılım oranını hesapla (% cinsinden)
    if total_tokens > 0:
        participation_rate = (len(votes) / total_tokens) * 100
    else:
        participation_rate = 0

    return render_template('core/results.html', election=election, results=results, participation_rate=participation_rate)


@core_bp.route('/vote/<token>', methods=['GET', 'POST'])
def vote(token):
    vote_token = VoteToken.query.filter_by(token=token, used=False).first()
    if not vote_token:
        flash('Geçersiz veya kullanılmış token.', 'danger')
        return render_template("errors/404.html")

    election = Election.query.get(vote_token.election_id)
    options = Option.query.filter_by(election_id=election.id).all()
    now = datetime.now()
    if not (election.start_date <= now <= election.end_date):
        flash('Bu oylama için oy verme süresi geçmiş veya henüz başlamamış.', 'warning')
        return render_template("errors/404.html")
    
    if request.method == 'POST':
        selected_option_id = request.form.get('option')
        if selected_option_id:
            new_vote = Votes(
                voter_id=vote_token.voter_id,
                election_id=election.id,
                option_id=selected_option_id,
                timestamp=db.func.current_timestamp()  
            )
            db.session.add(new_vote)            
            vote_token.used = True
            db.session.commit()
            
            flash('Oyunuz kaydedildi!', 'success')
            encrypted_election_id = encrypt_id(election.id)
            return redirect(url_for('core.election_results', encrypted_election_id=encrypted_election_id))

    return render_template('core/vote.html', election=election, options=options)



@core_bp.route("/create_election", methods=['GET', 'POST'])
@login_required
def create_election():
    voter_emails = request.form.getlist('voterEmail[]')
    valid_emails = []
    error = False
    for email in voter_emails:
        result = validate_email_address(email)
        if '@' in result:
            valid_emails.append(result)
        else:
            flash(f'Geçersiz e-posta adresi: {result}', 'warning')
            error = True
    if error:
        return redirect(url_for('core.create_election'))


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
            voter = Voter.query.filter_by(tc=tc).first()
            if voter:
                voter.name = name
                voter.surname = surname
                voter.email = email
            else:
                voter = Voter(tc=tc, name=name, surname=surname, email=email)
                db.session.add(voter)
            db.session.commit()
            token = create_vote_token_entry(voter.id, election.id)
            send_vote_link(voter, token, election)

        flash('Oylama başarıyla oluşturuldu!', "success")
        return redirect(url_for("core.create_election"))
        
    return render_template("core/index.html")
