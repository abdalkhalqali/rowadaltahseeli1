from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random, logging
from extensions import db
from models import User
from services.email_service import send_otp_email

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def _gen_otp():
    return str(random.randint(100000, 999999))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        gender   = request.form.get('gender', 'unknown')
        if gender not in ('male', 'female'):
            gender = 'unknown'

        if not all([name, email, password]):
            flash('يرجى ملء جميع الحقول', 'danger')
            return render_template('register.html')

        if not gender or gender == 'unknown':
            flash('يرجى تحديد الجنس', 'warning')
            return render_template('register.html')

        existing = User.query.filter_by(email=email).first()
        if existing:
            if existing.is_banned:
                flash('هذا البريد الإلكتروني محظور من المنصة', 'danger')
            else:
                flash('البريد الإلكتروني مسجّل مسبقاً', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('كلمة المرور يجب أن تكون 8 أحرف على الأقل', 'warning')
            return render_template('register.html')

        otp  = _gen_otp()
        user = User(
            name=name, email=email,
            password=generate_password_hash(password),
            gender=gender, grade='unknown', otp_code=otp,
            otp_expires=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(user)
        db.session.commit()
        try:
            from services.data_store import export_users
            export_users()
        except Exception:
            pass

        try:
            send_otp_email(email, name, otp)
            flash('تم إرسال رمز التحقق إلى بريدك الإلكتروني', 'success')
        except Exception as mail_err:
            logger.error(f"[OTP SEND FAIL] {type(mail_err).__name__}: {mail_err}")
            flash('تعذّر إرسال رمز التحقق، يرجى المحاولة مرة أخرى لاحقاً', 'danger')

        session['verify_email'] = email
        return redirect(url_for('auth.verify_otp'))

    return render_template('register.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('verify_email')
    if not email:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        user    = User.query.filter_by(email=email).first()

        if not user:
            flash('المستخدم غير موجود', 'danger')
            return redirect(url_for('auth.register'))

        if user.otp_expires and datetime.utcnow() > user.otp_expires:
            flash('انتهت صلاحية الرمز. أعد التسجيل.', 'danger')
            return redirect(url_for('auth.register'))

        if user.otp_code != entered:
            flash('رمز التحقق غير صحيح', 'danger')
            return render_template('verify_otp.html', email=email)

        user.is_verified = True
        user.otp_code    = None
        user.otp_expires = None
        db.session.commit()
        try:
            from services.data_store import export_users
            export_users()
        except Exception:
            pass

        login_user(user)
        session.pop('verify_email', None)
        flash('تم التحقق بنجاح! مرحباً بك في رواد التحصيلي 🎓', 'success')
        return redirect(url_for('auth.choice'))

    return render_template('verify_otp.html', email=email)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
            return render_template('login.html')

        if user.is_banned:
            flash('حسابك محظور من المنصة. تواصل مع الإدارة.', 'danger')
            return render_template('login.html')

        if not user.is_verified:
            session['verify_email'] = email
            otp = _gen_otp()
            user.otp_code    = otp
            user.otp_expires = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            try:
                send_otp_email(email, user.name, otp)
            except Exception as mail_err:
                logger.error(f"[OTP LOGIN FAIL] {type(mail_err).__name__}: {mail_err}")
            flash('حسابك غير مفعّل. تم إرسال رمز التحقق.', 'warning')
            return redirect(url_for('auth.verify_otp'))

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=remember)

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('auth.choice'))

    return render_template('login.html')

@auth_bp.route('/choice')
@login_required
def choice():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    if current_user.is_assessed:
        return redirect(url_for('student.dashboard'))
    return render_template('choice_page.html')

@auth_bp.route('/resend-otp')
def resend_otp():
    email = session.get('verify_email')
    if not email:
        return redirect(url_for('auth.register'))
    user = User.query.filter_by(email=email).first()
    if user:
        otp = _gen_otp()
        user.otp_code    = otp
        user.otp_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        try:
            send_otp_email(email, user.name, otp)
            flash('تم إعادة إرسال رمز التحقق', 'success')
        except Exception:
            flash('رمز التحقق الجديد: ' + otp, 'info')
    return redirect(url_for('auth.verify_otp'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('index'))
