from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user, current_user

from src.utils.email_utils import send_email, send_reset_email, send_update_email, send_verify_email
from src.utils.password_token_utils import create_password_reset_entry, verify_reset_token
from src.utils.email_validator import validate_email, EmailNotValidError
from src.utils.update_email_token_utils import create_update_email_entry, verify_update_token
from src.utils.verify_email_utils import create_email_verification_entry, verify_email_token
from src.utils.face_recognition import get_face_encoding, save_face_encoding, save_photo




from src import bcrypt, db
from src.accounts.models import User, PasswordResetToken, UpdateEmailToken

from .forms import LoginForm, RegisterForm, RequestResetForm, PasswordChangeForm_, EmailChangeForm, PasswordChangeForm

accounts_bp = Blueprint("accounts", __name__)

@accounts_bp.route('/update_email/<token>', methods=['GET'])
@login_required
def update_mail(token):
    user_id, new_email = verify_update_token(token)
    if not user_id:
        flash('Bu token kullanılmış ya da geçersiz', 'warning')
        return redirect(url_for('accounts.user_info', user_id=current_user.id, _external=True))
    
    if current_user.id != int(user_id):
        flash('Bu sayfayu görme yetkiniz yok.', 'danger')
        return render_template('errors/404.html')
    

    user = User.query.filter_by(id=user_id).first()
    if user:
        user.email = new_email
        token_entry = UpdateEmailToken.query.filter_by(user_id=user_id, token=token, used=False).first()
        token_entry.used = True
        db.session.commit()
        flash('E-posta başarıyla güncellendi.', 'success')
        return redirect(url_for('accounts.user_info', user_id=user_id, _external=True))

@accounts_bp.route('/user/<user_id>', methods=['GET', 'POST'])
@login_required
def user_info(user_id):
    if current_user.id != int(user_id):
        flash('Bu sayfayı görme yetkiniz yok.', 'danger')
        return render_template('errors/404.html')

    user = User.query.get(user_id)
    email_form = EmailChangeForm()
    password_form = PasswordChangeForm()

    is_voter = bool(user.tc)

    if email_form.validate_on_submit() and 'email' in request.form:
        new_email = email_form.email.data
        if User.query.filter_by(email=new_email).first():
            flash('Bu mail adresi zaten kayıtlı.', 'warning')
            return redirect(url_for('accounts.user_info', user_id=user_id, _external=True))

        token = create_update_email_entry(user.id, new_email)
        send_update_email(new_email, token)
        flash('Mail Gönderildi.', 'success')
        return redirect(url_for('accounts.user_info', user_id=user_id, _external=True))

    if password_form.validate_on_submit() and 'password' in request.form:
        if bcrypt.check_password_hash(user.password, password_form.current_password.data):
            if bcrypt.check_password_hash(user.password, password_form.new_password.data):
                flash('Yeni şifreniz eskisiyle aynı olamaz.', 'warning')
                return redirect(url_for('accounts.user_info', user_id=user_id, _external=True))
            user.password = bcrypt.generate_password_hash(password_form.new_password.data).decode('utf-8')
            db.session.commit()
            flash('Şifreniz başarıyla güncellendi.', 'success')
        else:
            flash('Mevcut şifre yanlış.', 'error')
        return redirect(url_for('accounts.user_info', user_id=user_id, _external=True))

    if is_voter:
        return render_template('accounts/user_voter_info.html', user=user, email_form=email_form, password_form=password_form)
    else:
        return render_template('accounts/user_info.html', user=user, email_form=email_form, password_form=password_form)




@accounts_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('core.create_election', _external=True))

    user_id = verify_reset_token(token)
    if not user_id:
        flash('Bu token kullanılmış ya da geçersiz', 'warning')
        return redirect(url_for('accounts.reset_password_request', _external=True))

    form = PasswordChangeForm_()
    if form.validate_on_submit():
        user = User.query.get(user_id)
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                flash('Yeni şifreniz eskisiyle aynı olamaz.', 'warning')
                return redirect(url_for('accounts.reset_password', token=token, _external=True))

            user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            reset_entry = PasswordResetToken.query.filter_by(user_id=user_id, token=token, used=False).first()
            if reset_entry:
                reset_entry.used = True
                db.session.commit()
            flash('Şifreniz başarıyla güncellendi.', 'success')
            return redirect(url_for('accounts.login', _external=True))
        else:
            flash('Kullanıcı bulunamadı', 'danger')
            return redirect(url_for('accounts.login', _external=True))
    return render_template('accounts/reset_password.html', form=form)





@accounts_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('core.create_election', _external=True))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = create_password_reset_entry(user.id)
            send_reset_email(user, token)
            flash('Şifre sıfırlama bağlantısını içeren mail gönderildi', 'info')
            return redirect(url_for('accounts.login', _external=True))
        else:
            flash('Bu mail adresi ile kayıtlı kullanıcı yok.', 'warning')
    return render_template('accounts/reset_password_request.html', title='Reset Password', form=form)



@accounts_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("Zaten kayıt oldunuz.", "info")
        return redirect(url_for("core.create_election", _external=True))

    if request.method == "POST":
        # Formdan gelen verileri al
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        tc = request.form.get("tc")
        name = request.form.get("name")
        surname = request.form.get("surname")
        is_voter = request.form.get("is_voter")  # Checkbox için
        voter_photo = request.files.get("voterPhoto")  # Fotoğraf dosyasını al

        # Doğrulama
        errors = []

        if not email or not password or not confirm_password:
            errors.append("Email ve şifre alanları doldurulmalıdır.")

        if password != confirm_password:
            errors.append("Şifreler uyuşmuyor.")

        if User.query.filter_by(email=email).first():
            errors.append("Bu email zaten kayıtlı.")

        if is_voter and (not tc or not name or not surname):
            errors.append("Seçmen hesapları için TC, isim ve soyisim zorunludur.")

        if is_voter and not voter_photo:
            errors.append("Seçmen hesapları için yüz fotoğrafı zorunludur.")

        if len(password) < 6 or len(password) > 25:
            errors.append("Şifre 6 ile 25 karakter arasında olmalıdır.")

        if len(tc or "") != 11 and is_voter:
            errors.append("TC kimlik numarası 11 haneli olmalıdır.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("accounts/register.html")

        # Fotoğrafı kaydet ve encoding işlemini gerçekleştir
        face_id = None
        if is_voter and voter_photo:
            photo_path = save_photo(voter_photo)  # Fotoğrafı kaydet
            face_encoding = get_face_encoding(photo_path)  # Encoding işlemini yap

            if face_encoding is None:
                flash("Yüklenen fotoğrafta yüz algılanamadı.", "danger")
                return render_template("accounts/register.html")

            face_id = save_face_encoding(face_encoding, photo_path)  # Encoding'i kaydet

        # Kullanıcı oluştur
        user = User(
            email=email,
            password=password,
            tc=tc if is_voter else None,
            name=name if is_voter else None,
            surname=surname if is_voter else None,
            face_id=face_id,  # Face ID'yi kaydediyoruz
        )
        db.session.add(user)
        db.session.commit()

        # Email doğrulama tokeni oluştur ve gönder
        token = create_email_verification_entry(user.id)
        send_verify_email(user, token)

        flash("Mailinize gelen onay linkine tıklayınız. Hoşgeldiniz!", "success")
        return redirect(url_for("accounts.login", _external=True))

    return render_template("accounts/register.html")

@accounts_bp.route('/verify_email/<token>', methods=['GET'])
def verify_email(token):
    if current_user.is_authenticated:
        return redirect(url_for('core.create_election', _external=True))
    user_id = verify_email_token(token)
    if not user_id:
        flash('Bu token kullanılmış ya da geçersiz.', 'warning')
        return redirect(url_for('accounts.login', _external=True))

    user = User.query.get(user_id)
    if user:
        if user.is_mail_approved:
            flash('Hesabınız zaten doğrulanmış.', 'info')
            return redirect(url_for('accounts.login', _external=True))
        user.is_mail_approved = True
        db.session.commit()
        flash('Hesabınız başarıyla doğrulandı.', 'success')
        return redirect(url_for('accounts.login', _external=True))
    else:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('accounts.login', _external=True))



@accounts_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("Zaten giriş yaptınız.", "info")
        return redirect(url_for("core.create_election", _external=True))

    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, request.form["password"]):
            if not user.is_mail_approved:
                flash("Hesabınız henüz doğrulanmış değil.", "warning")
                resend_url = url_for('accounts.resend_verification', user_id=user.id, _external=True)
                flash(f"Lütfen hesabınızı doğrulayın. <a href='{resend_url}'>Doğrulama linkini tekrar göndermek için tıklayınız.</a>", 'info')
                return render_template("accounts/login.html", form=form)

            # Kullanıcı giriş yapar
            login_user(user)

            # Yüz doğrulama kontrolü
            if not user.is_face_approved:
                verify_url = url_for('accounts.user_info', user_id=user.id, _external=True)
                flash(f"Başka kullanıcılar tarafından oylamalara seçmen olarak eklenebilmeniz için yüz doğrulaması yapmanız gerekmektedir. <a href='{verify_url}'>Doğrulamak için tıklayınız.</a>", "warning")
            
            return redirect(url_for("core.create_election", _external=True))
        else:
            flash("Geçersiz email veya şifre", "danger")
            return render_template("accounts/login.html", form=form)

    return render_template("accounts/login.html", form=form)

@accounts_bp.route("/resend_verification/<int:user_id>", methods=["GET"])
def resend_verification(user_id):
    user = User.query.get(user_id)

    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('accounts.login', _external=True))

    if user.is_mail_approved:
        flash('Hesabınız zaten doğrulanmış.', 'info')
        return redirect(url_for('accounts.login', _external=True))

    token = create_email_verification_entry(user.id)
    send_verify_email(user, token)
    
    flash(f"Doğrulama linki e-posta adresinize tekrar gönderildi.", 'info')
    return redirect(url_for('accounts.login', _external=True))



@accounts_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Çıkış yaptınız.", "success")
    return redirect(url_for("accounts.login", _external=True))
