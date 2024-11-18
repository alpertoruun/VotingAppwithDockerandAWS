from datetime import datetime, timezone, timedelta
from collections import defaultdict
from werkzeug.utils import secure_filename
import face_recognition
import cv2
import logging
import time
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from src.accounts.models import db, Election, Voter, Option, Votes, VoteToken, OptionCount, FaceRecognition
from src.utils.email_utils import send_vote_link
from src.utils.email_validator import validate_email_address, EmailNotValidError
from src.utils.vote_token_utils import create_vote_token_entry
from src.utils.encrypt_election_id import encrypt_id, decrypt_id
from src.utils.face_recognition import get_face_encoding, save_face_encoding, save_photo
import numpy as np



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
        return redirect(url_for('core.my_elections', _external=True))

    page = request.args.get('page', 1, type=int)
    per_page = 18
    sort_by = request.args.get('sort_by', 'name')  # Varsayılan sıralama alanı
    order = request.args.get('order', 'asc')
    search_query = request.args.get('search', '')

    # Sıralama ve arama işlemleri
    vote_tokens_query = VoteToken.query.filter_by(election_id=election_id).join(Voter, VoteToken.voter_id == Voter.id)
    if search_query:
        vote_tokens_query = vote_tokens_query.filter(
            (Voter.name.ilike(f"%{search_query}%")) |
            (Voter.surname.ilike(f"%{search_query}%")) |
            (Voter.tc.ilike(f"%{search_query}%")) |
            (Voter.email.ilike(f"%{search_query}%"))
        )

    if order == 'asc':
        vote_tokens_query = vote_tokens_query.order_by(getattr(Voter, sort_by).asc())
    else:
        vote_tokens_query = vote_tokens_query.order_by(getattr(Voter, sort_by).desc())

    # Paginasyon ve seçmen bilgisi
    vote_tokens_paginated = vote_tokens_query.paginate(page=page, per_page=per_page, error_out=True)
    voter_info = [(token, Voter.query.get(token.voter_id)) for token in vote_tokens_paginated.items]

    # AJAX isteği için tablo render işlemi
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'core/voter_table.html',
            voter_info=voter_info,
            pagination=vote_tokens_paginated,
            sort_by=sort_by,
            order=order,
            encrypted_election_id=encrypted_election_id
        )

    # Tüm sayfayı render et
    return render_template(
        'core/election_voters.html',
        election=election,
        voter_info=voter_info,
        pagination=vote_tokens_paginated,
        sort_by=sort_by,
        order=order,
        encrypted_election_id=encrypted_election_id
    )

from flask import send_from_directory
@core_bp.route('/static/uploads/<path:filename>')
@login_required
def custom_static(filename):
    uploads_dir = "/mnt/c/Users/alper.torun/Desktop/files/VotingAppwithDockerandAWS/static/uploads"
    return send_from_directory(uploads_dir, filename)

@core_bp.route('/my_elections')
@login_required
def my_elections():
    page = request.args.get('page', 1, type=int)
    per_page = 18
    sort_by = request.args.get('sort_by', 'created_at')  # Varsayılan sıralama alanı 'created_at'
    order = request.args.get('order', 'asc')
    search_query = request.args.get('search', '')

    # Sıralama ve arama için sorgu oluşturma
    elections_query = Election.query.filter(Election.creator_id == current_user.id)
    if search_query:
        elections_query = elections_query.filter(Election.title.ilike(f"%{search_query}%"))
    
    if order == 'asc':
        elections_query = elections_query.order_by(getattr(Election, sort_by).asc())
    else:
        elections_query = elections_query.order_by(getattr(Election, sort_by).desc())

    # Paginasyon ve şifreleme işlemi
    elections = elections_query.paginate(page=page, per_page=per_page, error_out=True)
    encrypted_elections = [(encrypt_id(election.id), election) for election in elections.items]

    # Eğer AJAX isteği ise, yalnızca tabloyu render edin
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'core/election_table.html',
            elections=encrypted_elections,
            pagination=elections,
            sort_by=sort_by,
            order=order
        )

    # Normal istekte tüm sayfayı render edin
    return render_template(
        'core/my_elections.html',
        elections=encrypted_elections,
        pagination=elections,
        sort_by=sort_by,
        order=order
    )



@core_bp.route('/election/<encrypted_election_id>')
def election_results(encrypted_election_id):
    election_id = decrypt_id(encrypted_election_id)
    if election_id is None:
        abort(404)  
    
    election = Election.query.get(election_id)
    if not election:
        abort(404)  
    
    option_counts = OptionCount.query.filter_by(election_id=election.id).all()

    if not option_counts:
        flash("Bu seçim için henüz oy sonuçları açıklanmamış.", "warning")
        return redirect(url_for('core.my_elections'))

    results = {Option.query.get(count.option_id).description: count.vote_count for count in option_counts}

    participation_rate = election.participation_rate

    return render_template('core/results.html', election=election, results=results, participation_rate=participation_rate)


from flask import jsonify, request

@core_bp.route('/face_control/<token>', methods=['GET', 'POST'])
def face_control(token):
    # Tokenin geçerliliğini kontrol et
    vote_token = VoteToken.query.filter_by(token=token, used=False).first()
    if not vote_token:
        return jsonify({"success": False, "message": "Geçersiz veya kullanılmış token."}), 400

    # Seçim tarihlerini kontrol et
    election = Election.query.get(vote_token.election_id)

    current_time = datetime.utcnow() + timedelta(hours=3)

    start_date_naive = election.start_date.replace(tzinfo=None)
    end_date_naive = election.end_date.replace(tzinfo=None)

    # Zaman bilgilerini kontrol amaçlı yazdırıyoruz
    print("Mevcut Zaman (Naive):", current_time)
    print("Başlangıç Tarihi (Naive):", start_date_naive)
    print("Bitiş Tarihi (Naive):", end_date_naive)
    if current_time < election.start_date or current_time > election.end_date:
        flash("Oylama saatleri dışındasınız.", "danger")
        return redirect(url_for("core.create_election"))

    # POST isteği olduğunda yüz tanıma işlemlerine geç
    if request.method == 'POST':
        voter = Voter.query.get(vote_token.voter_id)
        face_record = FaceRecognition.query.get(voter.face_id)

        if not face_record:
            return jsonify({"success": False, "message": "Yüz verisi bulunamadı."}), 400

        image_file = request.files.get('image')
        if not image_file:
            return jsonify({"success": False, "message": "Görüntü yüklenemedi."}), 400

        input_image = face_recognition.load_image_file(image_file)
        input_encoding = face_recognition.face_encodings(input_image)
        
        # YENİ: Yüz landmarks tespiti
        face_landmarks = face_recognition.face_landmarks(input_image)

        if len(input_encoding) == 0 or len(face_landmarks) == 0:
            return jsonify({"success": False, "message": "Yüz algılanamadı."}), 400

        # YENİ: Göz landmark'larını al
        landmarks = face_landmarks[0]
        left_eye = landmarks['left_eye']
        right_eye = landmarks['right_eye']

        # YENİ: Göz açıklık oranını hesapla
        def calculate_ear(eye_points):
            # Dikey mesafeler
            v1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
            v2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
            # Yatay mesafe
            h = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
            # EAR hesapla
            ear = (v1 + v2) / (2.0 * h)
            return ear

        # YENİ: Her iki göz için EAR hesapla
        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        EAR_THRESHOLD = 0.25

        known_encoding = np.frombuffer(face_record.encoding)
        match = face_recognition.compare_faces([known_encoding], input_encoding[0])

        # Eğer eşleşme varsa success olarak döndür, yoksa başarısız olarak işaretle
        if match[0]:
            encrypted_token = encrypt_id(token)
            # YENİ: Response'a göz durumu bilgisini ekle
            return jsonify({
                "success": "true",
                "ear_value": float(avg_ear),
                "eyes_closed": "true" if avg_ear < EAR_THRESHOLD else "false",
                "message": "Yüz doğrulama başarılı!",
                "redirect_url": url_for("core.vote", encrypted_token=encrypted_token, _external=True),
                "verification_stage": "face_verified"
            }), 200
        else:
            return jsonify({"success": "false", "message": "Yüz doğrulama başarısız!"}), 400

    return render_template('core/face_control.html', token=token)

@core_bp.route('/blink_verification', methods=['POST'])
def blink_verification():
    """
    Göz kırpma doğrulama endpoint'i
    """
    try:
        data = request.get_json()
        blink_count = data.get('blink_count', 0)
        token = data.get('token')
        
        if blink_count >= 3:  # Gerekli göz kırpma sayısına ulaşıldı
            encrypted_token = encrypt_id(token)
            return jsonify({
                "success": True,
                "message": "Göz kırpma doğrulaması başarılı!",
                "redirect_url": url_for("core.vote", encrypted_token=encrypted_token, _external=True)
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": f"Göz kırpma sayısı yetersiz. Mevcut: {blink_count}/3"
            }), 400

    except Exception as e:
        logging.error(f"Blink verification error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Göz kırpma doğrulaması sırasında bir hata oluştu."
        }), 500



@core_bp.route('/vote/<encrypted_token>', methods=['GET', 'POST'])
def vote(encrypted_token):
    original_token = decrypt_id(encrypted_token)
    if original_token is None:
        flash("Token geçersiz veya bozulmuş. Lütfen geçerli bir link kullanın.", "danger")
        return redirect(url_for("core.create_election"))

    # Token geçerliyse, ilgili VoteToken ve Election kayıtlarını al
    vote_token = VoteToken.query.filter_by(token=original_token, used=False).first()
    if not vote_token:
        flash("Bu token ile oy kullanılamaz veya zaten kullanılmış.", "danger")
        return redirect(url_for("core.create_election"))

    election = Election.query.get(vote_token.election_id)
    if not election:
        flash("İlgili seçim bilgisi bulunamadı.", "danger")
        return redirect(url_for("core.create_election"))

    # Seçenekleri (options) alıyoruz
    options = Option.query.filter_by(election_id=election.id).all()
    voter = Voter.query.filter_by(id=vote_token.voter_id).first()

    if request.method == 'POST':
        # Seçilen option_id'yi formdan al
        selected_option_id = request.form.get("option")
        if not selected_option_id:
            flash("Lütfen bir seçenek seçin.", "warning")
            return redirect(url_for("core.vote", encrypted_token=encrypted_token))

        # Vote kaydını oluştur ve veritabanına ekle
        vote = Votes(
            voter_id=voter.id,
            election_id=election.id,
            option_id=selected_option_id
        )
        db.session.add(vote)
        
        # Token'i kullanılmış olarak işaretle ve değişiklikleri kaydet
        vote_token.used = True
        db.session.commit()
        
        flash("Oyunuz başarıyla kaydedildi!", "success")
        return render_template("core/vote_confirmation.html", voter=voter)

    # Oy kullanma sayfası render ediliyor
    return render_template("core/vote.html", encrypted_token=encrypted_token, election=election, options=options)







@core_bp.route('/')
@login_required
def base():
    return redirect(url_for('core.create_election', _external=True))



ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        voter_photos = request.files.getlist('voterPhoto[]')

        # 1. E-posta ve TC doğrulama
        email_to_tc = defaultdict(set)
        face_encodings_list = []
        tc_face_map = {}
        error = False

        # Seçmen verilerini doğrula
        for tc, email, name, surname, photo in zip(voter_tcs, voter_emails, voter_names, voter_surnames, voter_photos):
            # E-posta doğrulama
            valid_email = validate_email_address(email)
            if not valid_email:
                flash(f'Geçersiz e-posta adresi: {email}', 'warning')
                error = True
                break

            if email in email_to_tc and tc not in email_to_tc[email]:
                flash(f'E-posta adresi {email} farklı TC kimlik numaralarıyla kullanılamaz.', 'warning')
                error = True
                break
            email_to_tc[email].add(tc)

            # Yüz tanıma doğrulaması
            if photo and allowed_file(photo.filename):
                photo_path = save_photo(photo)  # Fotoğrafı rastgele isimle kaydet
                face_encoding = get_face_encoding(photo_path)

                if face_encoding is not None and face_encoding.size > 0:
                    for existing_encoding, existing_tc in face_encodings_list:
                        match = face_recognition.compare_faces([existing_encoding], face_encoding, tolerance=0.6)
                        if match[0] and existing_tc != tc:
                            flash(f"Yüz verisi başka bir seçmenle eşleşiyor: {tc} - {existing_tc}", "warning")
                            error = True
                            break

                    if error:
                        break

                    # Yeni yüz encoding'i listeye ekle
                    face_encodings_list.append((face_encoding, tc))
                    tc_face_map[tc] = {"encoding": face_encoding, "photo_path": photo_path}
                else:
                    flash(f"{tc} TC kimlik numarasına sahip seçmen için geçerli yüz verisi bulunamadı.", "warning")
                    error = True
                    break

        # Eğer herhangi bir hata varsa işlemi durdur
        if error:
            return redirect(url_for('core.create_election', _external=True))

        # 2. Tüm kontroller başarılı, seçim oluşturma işlemini başlat
        election = Election(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            creator_id=current_user.id
        )
        db.session.add(election)
        db.session.commit()

        # Seçenekleri ekle
        for option_desc in options:
            option = Option(description=option_desc, election_id=election.id)
            db.session.add(option)

        # Seçmenleri kaydet
        for tc, name, surname, email in zip(voter_tcs, voter_names, voter_surnames, voter_emails):
            voter = Voter.query.filter_by(tc=tc).first()
            face_data = tc_face_map.get(tc)

            if voter:
                # Mevcut seçmen bilgilerini güncelle
                voter.name = name
                voter.surname = surname
                voter.email = email
                if face_data:
                    if voter.face_id:
                        face_recognition_entry = FaceRecognition.query.get(voter.face_id)
                        face_recognition_entry.encoding = face_data["encoding"]
                        face_recognition_entry.image_path = face_data["photo_path"]
                    else:
                        face_id = save_face_encoding(face_data["encoding"], face_data["photo_path"])
                        voter.face_id = face_id
            else:
                # Yeni seçmen oluştur
                face_id = save_face_encoding(face_data["encoding"], face_data["photo_path"]) if face_data else None
                voter = Voter(tc=tc, name=name, surname=surname, email=email, face_id=face_id)
                db.session.add(voter)

            db.session.commit()

            # Oylama token'ı oluştur ve e-posta gönder
            token = create_vote_token_entry(voter.id, election.id)
            send_vote_link(voter, token, election)

        flash('Oylama başarıyla oluşturuldu!', "success")
        return redirect(url_for("core.my_elections", _external=True))

    return render_template("core/index.html")
