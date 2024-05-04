from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user, current_user

from src.utils.email_utils import send_email, send_reset_email, send_update_email
from src.utils.password_token_utils import create_password_reset_entry, verify_reset_token
from src.utils.email_validator import validate_email, EmailNotValidError
from src.utils.update_email_token_utils import create_update_email_entry, verify_update_token



from src import bcrypt, db
from src.accounts.models import User, PasswordResetToken, UpdateEmailToken

from .forms import LoginForm, RegisterForm, RequestResetForm, PasswordChangeForm, EmailChangeForm, PasswordChangeForm

accounts_bp = Blueprint("accounts", __name__)

@accounts_bp.route('/update_email/<token>', methods=['GET'])
@login_required
def update_mail(token):
    user_id, new_email = verify_update_token(token)
    if not user_id:
        flash('This is an invalid or expired token', 'warning')
        return redirect(url_for('accounts.user_info', user_id=current_user.id))
    
    if current_user.id != int(user_id):
        flash('Bu sayfayi görme yetkiniz yok.', 'danger')
        return render_template('errors/404.html')
    

    user = User.query.filter_by(id=user_id).first()
    if user:
        user.email = new_email
        token_entry = UpdateEmailToken.query.filter_by(user_id=user_id, token=token, used=False).first()
        token_entry.used = True
        db.session.commit()
        flash('E-posta başarıyla güncellendi.', 'success')
        return redirect(url_for('accounts.user_info', user_id=user_id))

@accounts_bp.route('/user/<user_id>', methods=['GET', 'POST'])
@login_required
def user_info(user_id):
    if current_user.id != int(user_id):
        flash('Bu sayfayi görme yetkiniz yok.', 'danger')
        return render_template('errors/404.html')

    user = User.query.get(user_id)
    email_form = EmailChangeForm()
    password_form = PasswordChangeForm()

    if email_form.validate_on_submit() and 'email' in request.form:
        new_email = email_form.email.data
        if User.query.filter_by(email=new_email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('accounts.user_info', user_id=user_id))

        token = create_update_email_entry(user.id, new_email)
        send_update_email(new_email, token)
        flash('Mail Gönderildi.', 'success')
        return redirect(url_for('accounts.user_info', user_id=user_id))

    if password_form.validate_on_submit() and 'password' in request.form:
        if bcrypt.check_password_hash(user.password, password_form.current_password.data):
            user.password = bcrypt.generate_password_hash(password_form.new_password.data).decode('utf-8')
            db.session.commit()
            flash('Şifreniz başarıyla güncellendi.', 'success')
        else:
            flash('Mevcut şifre yanlış.', 'error')
        return redirect(url_for('accounts.user_info', user_id=user_id))

    return render_template('accounts/user_info.html', user=user, email_form=email_form, password_form=password_form)




@accounts_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('core.create_election'))

    user_id = verify_reset_token(token)
    if not user_id:
        flash('This is an invalid or expired token', 'warning')
        return redirect(url_for('accounts.reset_password_request'))

    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = User.query.get(user_id)
        if user:
            user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            reset_entry = PasswordResetToken.query.filter_by(user_id=user_id, token=token, used=False).first()
            if reset_entry:
                reset_entry.used = True
                db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('accounts.login'))
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('accounts.login'))
    return render_template('accounts/reset_password.html', form=form)

@accounts_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('core.create_election'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = create_password_reset_entry(user.id)
            send_reset_email(user, token)
            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('accounts.login'))
        else:
            flash('No account with that email address exists.', 'warning')
    return render_template('accounts/reset_password_request.html', title='Reset Password', form=form)



@accounts_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("You are already registered.", "info")
        return redirect(url_for("core.create_election"))
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        user = User(email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        send_email("Welcome to Our App!", user.email, "Thank you for signing up. We're glad to have you!")
        login_user(user)
        flash("You registered and are now logged in. Welcome!", "success")
        return redirect(url_for("core.create_election"))

    return render_template("accounts/register.html", form=form)


@accounts_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("core.create_election"))
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect(url_for("core.create_election"))
        else:
            flash("Invalid email and/or password.", "danger")
            return render_template("accounts/login.html", form=form)
    return render_template("accounts/login.html", form=form)




@accounts_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You were logged out.", "success")
    return redirect(url_for("accounts.login"))
