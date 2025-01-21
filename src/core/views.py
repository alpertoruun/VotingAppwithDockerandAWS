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
from src.accounts.models import db, Election, Option, Votes, VoteToken, OptionCount, FaceRecognition, User, TemporaryBlockedUser
from src.utils.email_utils import send_vote_link
from src.utils.email_validator import validate_email_address, EmailNotValidError
from src.utils.vote_token_utils import create_vote_token_entry
from src.utils.encrypt_election_id import encrypt_id, decrypt_id
from src.utils.face_recognition import get_face_encoding, save_face_encoding, save_photo
import numpy as np
import logging
import socket

logging.basicConfig(
    filename='app.log', 
    level=logging.DEBUG, 
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)


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
    sort_by = request.args.get('sort_by', 'name')  
    order = request.args.get('order', 'asc')
    search_query = request.args.get('search', '')

    # Sıralama ve arama işlemleri
    vote_tokens_query = (
        VoteToken.query.filter_by(election_id=election_id)
        .join(User, VoteToken.user_id == User.id)
    )

    if search_query:
        vote_tokens_query = vote_tokens_query.filter(
            (User.name.ilike(f"%{search_query}%")) |
            (User.surname.ilike(f"%{search_query}%")) |
            (User.tc.ilike(f"%{search_query}%")) |
            (User.email.ilike(f"%{search_query}%"))
        )

    if order == 'asc':
        vote_tokens_query = vote_tokens_query.order_by(getattr(User, sort_by).asc())
    else:
        vote_tokens_query = vote_tokens_query.order_by(getattr(User, sort_by).desc())

    # Paginasyon ve kullanıcı bilgisi
    vote_tokens_paginated = vote_tokens_query.paginate(page=page, per_page=per_page, error_out=True)
    voter_info = [(token, User.query.get(token.user_id)) for token in vote_tokens_paginated.items]

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
    current_dir = os.getcwd()
    uploads_dir = os.path.join(current_dir, "static", "uploads")
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
@login_required
def face_control(token):
    # Tokenin geçerliliğini kontrol et
    vote_token = VoteToken.query.filter_by(token=token, used=False).first()
    if not vote_token:
        flash("Geçersiz veya kullanılmış token.", "danger")
        return redirect(url_for("core.create_election"))

    if current_user.id != int(vote_token.user_id):
        flash('Bu sayfayı görme yetkiniz yok.', 'danger')
        return render_template('errors/404.html')

    if TemporaryBlockedUser.is_user_blocked(vote_token.user_id):
        flash("Çok fazla başarısız deneme yaptınız. Lütfen 30 dakika sonra tekrar deneyin.", "danger")
        return redirect(url_for("core.create_election"))

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
        voter = User.query.get(vote_token.user_id)
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

@core_bp.route('/block_user', methods=['POST'])
def block_user():
    data = request.get_json()
    token = data.get('token')
    
    vote_token = VoteToken.query.filter_by(token=token, used=False).first()
    if not vote_token:
        return jsonify({"blocked": False}), 400

    # Kullanıcıyı bloke et
    block = TemporaryBlockedUser(user_id=vote_token.user_id)
    db.session.add(block)
    db.session.commit()

    return jsonify({"blocked": True}), 200

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

EAR_THRESHOLD = 0.25  # Göz kırpma eşik değeri

@core_bp.route('/face_approve/<encrypted_user_id>', methods=['GET', 'POST'])
@login_required
def face_approve(encrypted_user_id):
    try:
        user_id = decrypt_id(encrypted_user_id)
        user = User.query.get(user_id)

        if not user:
            return jsonify({"success": False, "message": "Kullanıcı bulunamadı."}), 400

        if current_user.id != user.id:
            return jsonify({"success": False, "message": "Bu işlem için yetkiniz yok."}), 403

        if request.method == 'POST':
            image_file = request.files.get('image')
            if not image_file:
                return jsonify({"success": False, "message": "Görüntü yüklenemedi."}), 400

            try:
                input_image = face_recognition.load_image_file(image_file)
                input_encoding = face_recognition.face_encodings(input_image)
                face_landmarks = face_recognition.face_landmarks(input_image)

                if len(input_encoding) == 0 or len(face_landmarks) == 0:
                    return jsonify({"success": False, "message": "Yüz algılanamadı."}), 400

                # Face record kontrolü
                face_record = FaceRecognition.query.get(user.face_id)
                if not face_record:
                    return jsonify({"success": False, "message": "Yüz verisi bulunamadı."}), 400

                # Encoding karşılaştırma
                known_encoding = np.frombuffer(face_record.encoding)
                known_encoding = known_encoding.reshape((128,))
                match = face_recognition.compare_faces([known_encoding], input_encoding[0], tolerance=0.6)

                if match[0]:
                    # Göz durumu hesaplama
                    landmarks = face_landmarks[0]
                    left_eye = landmarks.get('left_eye')
                    right_eye = landmarks.get('right_eye')

                    if not left_eye or not right_eye:
                        return jsonify({"success": False, "message": "Göz noktaları tespit edilemedi."}), 400

                    def calculate_ear(eye_points):
                        try:
                            v1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
                            v2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
                            h = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
                            return (v1 + v2) / (2.0 * h) if h > 0 else 0
                        except Exception as e:
                            logging.error(f"EAR hesaplama hatası: {str(e)}")
                            return 0

                    left_ear = calculate_ear(left_eye)
                    right_ear = calculate_ear(right_eye)
                    avg_ear = (left_ear + right_ear) / 2.0

                    return jsonify({
                        "success": True,
                        "ear_value": float(avg_ear),
                        "eyes_closed": bool(avg_ear < EAR_THRESHOLD),
                        "message": "Yüz doğrulama başarılı!",
                        "verification_stage": "face_verified",
                        "encrypted_user_id": encrypted_user_id
                    }), 200

                else:
                    return jsonify({
                        "success": False,
                        "message": "Yüz eşleşmedi."
                    }), 400

            except Exception as e:
                logging.error(f"Face processing error: {str(e)}")
                return jsonify({
                    "success": False,
                    "message": f"İşlem hatası: {str(e)}"
                }), 500

        return render_template('core/face_approve.html', user=user, encrypted_user_id=encrypted_user_id)

    except Exception as e:
        logging.exception(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Beklenmeyen bir hata oluştu."
        }), 500

@core_bp.route('/blink_verification_register', methods=['POST'])
@login_required
def blink_verification_register():
    try:
        data = request.get_json()
        blink_count = data.get('blink_count', 0)
        encrypted_user_id = data.get('encrypted_user_id')
        
        if not encrypted_user_id:
            return jsonify({
                "success": False,
                "message": "Kullanıcı ID'si gerekli"
            }), 400
            
        user_id = decrypt_id(encrypted_user_id)
        user = User.query.get(user_id)
        
        if not user or current_user.id != user.id:
            return jsonify({
                "success": False,
                "message": "Geçersiz kullanıcı"
            }), 400
        
        if blink_count >= 3:
            try:
                user.is_face_approved = True
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Göz kırpma doğrulaması başarılı!",
                    "redirect_url": url_for("accounts.user_info", user_id=user_id)
                }), 200
            except Exception as db_error:
                db.session.rollback()
                logging.error(f"Database error: {str(db_error)}")
                return jsonify({
                    "success": False,
                    "message": "Veritabanı işlemi sırasında hata oluştu."
                }), 500
        else:
            return jsonify({
                "success": False,
                "message": f"Göz kırpma sayısı yetersiz. Mevcut: {blink_count}/3"
            }), 400

    except Exception as e:
        logging.error(f"Blink verification error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Beklenmeyen bir hata oluştu."
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
    voter = User.query.filter_by(id=vote_token.user_id).first()

    if request.method == 'POST':
        # Seçilen option_id'yi formdan al
        selected_option_id = request.form.get("option")
        if not selected_option_id:
            flash("Lütfen bir seçenek seçin.", "warning")
            return redirect(url_for("core.vote", encrypted_token=encrypted_token))

        # Vote kaydını oluştur ve veritabanına ekle
        vote = Votes(
            user_id=voter.id,
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
        # Form verilerini al
        title = request.form.get('title')
        description = request.form.get('description')
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        options = request.form.getlist('options[]')
        voter_tcs = request.form.getlist('voterTc[]')

        # Hata kontrolü
        error = False
        # TC'lerin benzersiz olduğunu kontrol et
        if len(voter_tcs) != len(set(voter_tcs)):
            flash("Aynı TC kimlik numarası birden fazla kez eklenemez.", "warning")
            return redirect(url_for('core.create_election'), _external=True)

        # Kullanıcıları doğrula
        valid_users = []
        used_tcs = set()  # Kullanılan TC'leri takip et
        
        for tc in voter_tcs:
            # TC zaten eklenmişse atla
            if tc in used_tcs:
                continue
                
            user = User.query.filter_by(tc=tc).first()
            if not user or not user.is_mail_approved or not user.is_face_approved:
                flash(f"{tc} kimlik numarasına sahip onaylı bir kullanıcı bulunamadı.", "warning")
                error = True
                break
                
            valid_users.append(user)
            used_tcs.add(tc)  # TC'yi kullanılanlar listesine ekle

        # Hata varsa formu tekrar yükle
        if error:
            return redirect(url_for('core.create_election'), _external=True)
        # Kullanıcıları doğrula
        valid_users = []
        for tc in voter_tcs:
            user = User.query.filter_by(tc=tc).first()
            if not user or not user.is_mail_approved or not user.is_face_approved:
                flash(f"{tc} kimlik numarasına sahip onaylı bir kullanıcı bulunamadı.", "warning")
                error = True
                break
            valid_users.append(user)

        # Hata varsa formu tekrar yükle
        if error:
            return redirect(url_for('core.create_election', _external=True))

        # Seçim oluştur
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
        db.session.commit()
        # Seçmenleri ekle
        for user in valid_users:
            vote_token = create_vote_token_entry(user.id, election.id)
            send_vote_link(user, vote_token, election)

        db.session.commit()
        flash('Oylama başarıyla oluşturuldu!', "success")
        return redirect(url_for("core.my_elections", _external=True))

    return render_template("core/index.html", _external=True)

@core_bp.route('/get_user_info', methods=['POST'])
@login_required
def get_user_info():
    tc = request.json.get('tc')
    user = User.query.filter_by(tc=tc).first()

    if not user or not user.is_mail_approved or not user.is_face_approved:
        return jsonify({'error': f"{tc} kimlik numarasına sahip onaylı bir kullanıcı bulunamadı."}), 400

    return jsonify({
        'name': user.name,
        'surname': user.surname,
        'email': user.email
    })

@core_bp.route('/health', methods=['GET'])
def health_check():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    
    return jsonify({
        'ip': ip_address
    }), 200


@core_bp.route('/joined_elections', methods=['GET'])
@login_required
def joined_elections():
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    search = request.args.get('search', '')
    per_page = 10

    # Base query
    elections_query = Election.query.join(VoteToken, VoteToken.election_id == Election.id)\
        .filter(VoteToken.user_id == current_user.id)
    
    # Search functionality
    if search:
        elections_query = elections_query.filter(Election.title.ilike(f"%{search}%"))
    
    # Sorting
    if order == 'asc':
        elections_query = elections_query.order_by(getattr(Election, sort_by).asc())
    else:
        elections_query = elections_query.order_by(getattr(Election, sort_by).desc())
    
    # Pagination ve şifreleme işlemi
    elections = elections_query.paginate(page=page, per_page=per_page, error_out=True)
    encrypted_elections = [(encrypt_id(election.id), election) for election in elections.items]

    # AJAX isteği kontrolü
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('core/joined_election_table.html',
                             elections=encrypted_elections,
                             pagination=elections,
                             sort_by=sort_by,
                             order=order)

    return render_template('core/joined_elections.html',
                         elections=encrypted_elections,
                         pagination=elections,
                         sort_by=sort_by,
                         order=order)