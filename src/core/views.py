from datetime import datetime
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from src.accounts.models import db, Election, Voter, Option, Votes, VoteToken
from src.utils.email_utils import send_vote_link
from src.utils.email_validator import validate_email_address, EmailNotValidError
from src.utils.vote_token_utils import create_vote_token_entry
from src.utils.encrypt_election_id import encrypt_id, decrypt_id


core_bp = Blueprint("core", __name__)



@core_bp.route('/election/<encrypted_election_id>/voters')
@login_required
def election_voters(encrypted_election_id):
    election_id = decrypt_id(encrypted_election_id)
    if not election_id:
        abort(404, description="Geçersiz seçim ID'si")

    election = Election.query.get(election_id)
    if not election:
        abort(404, description="Seçim bulunamadı")

    if current_user.id != election.creator_id:
        flash('Bu sayfayı görüntüleme yetkiniz yok.', 'warning')
        return redirect(url_for('core.index', _external=True))

    page = request.args.get('page', 1, type=int)
    per_page = 18
    vote_tokens_query = VoteToken.query.filter_by(election_id=election_id).join(Voter, VoteToken.voter_id == Voter.id)
    vote_tokens_paginated = vote_tokens_query.paginate(page=page, per_page=per_page, error_out=True)
    voter_info = [(token, Voter.query.get(token.voter_id)) for token in vote_tokens_paginated.items]
    print(voter_info)

    return render_template('core/election_voters.html', election=election, voter_info=voter_info, pagination=vote_tokens_paginated)



@core_bp.route('/my_elections')
@login_required
def my_elections():
    page = request.args.get('page', 1, type=int)
    per_page = 18
    elections_query = Election.query.filter_by(creator_id=current_user.id)
    elections = elections_query.paginate(page=page, per_page=per_page, error_out=True)
    encrypted_elections = [(encrypt_id(election.id), election) for election in elections.items]
    return render_template('core/my_elections.html', elections=encrypted_elections, pagination=elections)





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
            return redirect(url_for('core.election_results', encrypted_election_id=encrypted_election_id, _external=True))

    return render_template('core/vote.html', election=election, options=options)

@core_bp.route('/')
@login_required
def base():
    return redirect(url_for('core.create_election', _external=True))



@core_bp.route("/create_election", methods=['GET', 'POST'])
@login_required
def create_election():

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
        voter_data = zip(voter_tcs, voter_emails)
        email_to_tc = defaultdict(set)
        error = False
        for tc, email in voter_data:
            valid_email = validate_email_address(email)
            if valid_email is None:  
                flash(f'Geçersiz e-posta adresi: {email}', 'warning')
                error = True
                break
            if email in email_to_tc and tc not in email_to_tc[email]:
                flash(f'E-posta adresi {email} farklı TC kimlik numaralarıyla kullanılamaz.', 'warning')
                error = True
                break
            email_to_tc[email].add(tc)

        if error:
            return redirect(url_for('core.create_election', _external=True))
        voter_expanded_data = zip(voter_tcs, voter_names, voter_surnames, voter_emails)
        for tc, name, surname, email in voter_expanded_data:
            for other_tc, other_name, other_surname, other_email in voter_expanded_data:
                if tc == other_tc and ((name, surname) != (other_name, other_surname) or email != other_email):
                    flash(f'Aynı TC kimlik numarasına sahip ({tc}) seçmenlerin isim, soyisim veya e-posta adresleri farklı olamaz.', 'warning')
                    error = True
                    break
            if error:
                break
        if error:
            return redirect(url_for('core.create_election', _external=True))



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
        return redirect(url_for("core.my_elections", _external=True))
        
    return render_template("core/index.html")