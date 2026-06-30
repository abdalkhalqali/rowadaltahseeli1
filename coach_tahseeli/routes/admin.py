from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Question, Evaluation, Competition
from services.question_service import bulk_add_questions
from services.ai_service import generate_questions_from_text, fix_import_code
import json, os, uuid, ast
from werkzeug.utils import secure_filename

_DEFAULT_UPLOAD = os.path.join(os.path.dirname(__file__), '..', 'static', 'question_images')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def _get_upload_folder():
    from flask import current_app
    base = current_app.config.get('PERSISTENT_UPLOADS', os.path.join(os.path.dirname(__file__), '..', 'static'))
    return os.path.join(base, 'question_images')

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

admin_bp = Blueprint('admin', __name__)

SUPER_ADMIN_EMAIL = 'abdualkhaliqali7@gmail.com'

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('هذه الصفحة للمشرفين فقط', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def super_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('هذه الصفحة للمشرفين فقط', 'danger')
            return redirect(url_for('auth.login'))
        if current_user.email.lower() != SUPER_ADMIN_EMAIL.lower():
            flash('هذه الصفحة للمشرف العام فقط', 'danger')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    import os
    from flask import current_app
    from sqlalchemy import inspect as sa_inspect

    stats = {
        'users':       User.query.filter_by(is_admin=False).count(),
        'questions':   Question.query.filter_by(is_active=True).count(),
        'evals':       Evaluation.query.count(),
        'competitions': Competition.query.count(),
    }
    recent_users  = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).limit(10).all()
    recent_evals  = Evaluation.query.order_by(Evaluation.created_at.desc()).limit(10).all()
    subject_stats = _get_subject_stats()

    # معلومات قاعدة البيانات — تحذير إن لم تكن على قرص دائم
    db_uri  = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    db_path = db_uri.replace('sqlite:///', '') if 'sqlite' in db_uri else ''
    db_persistent = db_path.startswith('/var/data') if db_path else False
    db_size_mb = round(os.path.getsize(db_path) / 1024 / 1024, 2) if db_path and os.path.exists(db_path) else 0

    db_info = {
        'persistent': db_persistent,
        'path':       db_path,
        'size_mb':    db_size_mb,
    }

    return render_template('admin_dashboard.html', stats=stats,
                           recent_users=recent_users,
                           recent_evals=recent_evals,
                           subject_stats=subject_stats,
                           db_info=db_info)


@admin_bp.route('/db/backup')
@login_required
@admin_required
def db_backup():
    """تحميل نسخة احتياطية من قاعدة البيانات"""
    import os
    from flask import current_app, send_file
    from datetime import datetime
    db_uri  = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    db_path = db_uri.replace('sqlite:///', '')
    if not db_path or not os.path.exists(db_path):
        flash('⚠️ ملف قاعدة البيانات غير موجود', 'danger')
        return redirect(url_for('admin.dashboard'))
    filename = f"tahseeli_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return send_file(db_path, as_attachment=True, download_name=filename)

def _get_subject_stats():
    subjects = ['physics', 'chemistry', 'biology', 'math']
    result   = {}
    for s in subjects:
        result[s] = {
            'questions': Question.query.filter_by(subject=s, is_active=True).count(),
            'evals':     Evaluation.query.filter_by(subject=s).count(),
        }
    return result

@admin_bp.route('/questions', methods=['GET'])
@login_required
@admin_required
def questions():
    subject    = request.args.get('subject', '')
    difficulty = request.args.get('difficulty', '')
    search     = request.args.get('search', '').strip()
    page       = request.args.get('page', 1, type=int)

    q = Question.query.filter_by(is_active=True)
    if subject:    q = q.filter_by(subject=subject)
    if difficulty: q = q.filter_by(difficulty=difficulty)
    if search:     q = q.filter(Question.text.ilike(f'%{search}%'))

    pagination = q.order_by(Question.created_at.desc()).paginate(page=page, per_page=25)
    return render_template('questions_management.html',
                           pagination=pagination, subject=subject,
                           difficulty=difficulty, search=search)

# ── رفع صورة لسؤال ──────────────────────────────────────────
@admin_bp.route('/questions/upload-image', methods=['POST'])
@login_required
@admin_required
def upload_question_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'لم يتم اختيار ملف'})
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'لم يتم اختيار ملف'})
    if not _allowed(file.filename):
        return jsonify({'success': False, 'error': 'نوع الملف غير مسموح به'})

    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    ext      = file.filename.rsplit('.', 1)[1].lower()
    filename = f"q_{uuid.uuid4().hex[:12]}.{ext}"
    filepath = os.path.join(folder, filename)
    file.save(filepath)
    url = f"/static/question_images/{filename}"
    return jsonify({'success': True, 'url': url, 'filename': filename})

# ── حذف صورة سؤال ────────────────────────────────────────────
@admin_bp.route('/questions/<int:qid>/delete-image', methods=['POST'])
@login_required
@admin_required
def delete_question_image(qid):
    q = Question.query.get_or_404(qid)
    if q.image_path:
        filepath = os.path.join(_get_upload_folder(), os.path.basename(q.image_path))
        if os.path.exists(filepath):
            os.remove(filepath)
        q.image_path = ''
        db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/questions/add', methods=['POST'])
@login_required
@admin_required
def add_question():
    data = request.get_json()
    q = Question(
        text=data['text'], option_a=data['option_a'],
        option_b=data['option_b'], option_c=data['option_c'],
        option_d=data['option_d'], answer=data['answer'].upper(),
        explanation=data.get('explanation', ''),
        subject=data['subject'], difficulty=data.get('difficulty', 'medium'),
        lesson=data.get('lesson', ''), grade=data.get('grade', 'grade_12'),
        chapter=data.get('chapter', ''), exam_type=data.get('exam_type', 'general'),
        image_path=data.get('image_path', ''),
        code_snippet=data.get('code_snippet', ''),
        code_type=data.get('code_type', 'python'),
        created_by=current_user.id
    )
    db.session.add(q)
    db.session.commit()
    try:
        from services.data_store import export_questions
        export_questions()
    except Exception:
        pass
    return jsonify({'success': True, 'id': q.id})

@admin_bp.route('/questions/<int:qid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(qid):
    q = Question.query.get_or_404(qid)
    # حذف الصورة من الملفات
    if q.image_path:
        filepath = os.path.join(_get_upload_folder(), os.path.basename(q.image_path))
        if os.path.exists(filepath):
            os.remove(filepath)
    q.is_active = False
    db.session.commit()
    try:
        from services.data_store import export_questions
        export_questions()
    except Exception:
        pass
    return jsonify({'success': True})

@admin_bp.route('/questions/<int:qid>/edit', methods=['POST'])
@login_required
@admin_required
def edit_question(qid):
    q    = Question.query.get_or_404(qid)
    data = request.get_json()
    for field in ['text', 'option_a', 'option_b', 'option_c', 'option_d',
                  'answer', 'explanation', 'subject', 'difficulty', 'lesson',
                  'grade', 'chapter', 'exam_type', 'image_path',
                  'code_snippet', 'code_type']:
        if field in data:
            setattr(q, field, data[field])
    db.session.commit()
    try:
        from services.data_store import export_questions
        export_questions()
    except Exception:
        pass
    return jsonify({'success': True})

@admin_bp.route('/users')
@login_required
@super_admin_required
def users():
    page  = request.args.get('page', 1, type=int)
    users = (User.query.filter_by(is_admin=False)
             .order_by(User.created_at.desc())
             .paginate(page=page, per_page=20))
    return render_template('admin_users.html', users=users)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@super_admin_required
def create_user():
    from werkzeug.security import generate_password_hash
    data     = request.get_json(silent=True) or {}
    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    gender   = data.get('gender', 'unknown')
    grade    = data.get('grade', 'grade_12')

    if not name or not email or not password:
        return jsonify({'success': False, 'error': 'الاسم والبريد وكلمة المرور مطلوبة'})
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'})
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'البريد الإلكتروني مسجّل مسبقاً'})

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        plain_password=password,
        gender=gender,
        grade=grade,
        is_verified=True,
    )
    db.session.add(user)
    db.session.commit()
    try:
        from services.data_store import export_users
        export_users()
    except Exception:
        pass
    return jsonify({'success': True, 'uid': user.id, 'name': user.name})


@admin_bp.route('/users/<int:uid>/password')
@login_required
@super_admin_required
def view_password(uid):
    user = User.query.get_or_404(uid)
    if user.plain_password:
        return jsonify({'success': True, 'password': user.plain_password, 'email': user.email})
    return jsonify({'success': False, 'error': 'كلمة المرور غير متاحة (سجّل المستخدم بنفسه)'})


@admin_bp.route('/users/<int:uid>/reset-password', methods=['POST'])
@login_required
@super_admin_required
def reset_password(uid):
    from werkzeug.security import generate_password_hash
    data        = request.get_json(silent=True) or {}
    new_pass    = (data.get('password') or '').strip()
    if len(new_pass) < 6:
        return jsonify({'success': False, 'error': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'})
    user = User.query.get_or_404(uid)
    user.password       = generate_password_hash(new_pass)
    user.plain_password = new_pass
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/users/<int:uid>')
@login_required
@super_admin_required
def user_detail(uid):
    user  = User.query.get_or_404(uid)
    evals = (Evaluation.query.filter_by(user_id=uid)
             .order_by(Evaluation.created_at.desc()).all())

    from models.pro_license_question import ProLicenseResult, DailyTrainingSession, PRO_STANDARDS
    pro_results = (ProLicenseResult.query.filter_by(user_id=uid)
                   .order_by(ProLicenseResult.created_at.desc()).limit(50).all())
    pro_daily   = (DailyTrainingSession.query.filter_by(user_id=uid, completed=True)
                   .order_by(DailyTrainingSession.created_at.desc()).limit(20).all())

    return render_template('admin_user_detail.html',
        user=user, evals=evals,
        pro_results=pro_results,
        pro_daily=pro_daily,
        PRO_STANDARDS=PRO_STANDARDS,
    )


@admin_bp.route('/users/<int:uid>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete_user(uid):
    user = User.query.get_or_404(uid)
    if user.is_admin:
        return jsonify({'success': False, 'error': 'لا يمكن حذف المشرف'})
    from models.evaluation import Evaluation
    from models.notification import Notification
    from models.community import CommunityPost
    from models.direct_message import DirectMessage
    from models.story import Story
    Story.query.filter_by(user_id=uid).delete()
    Evaluation.query.filter_by(user_id=uid).delete()
    Notification.query.filter_by(user_id=uid).delete()
    DirectMessage.query.filter(
        (DirectMessage.sender_id == uid) | (DirectMessage.recipient_id == uid)
    ).delete()
    CommunityPost.query.filter_by(user_id=uid).delete()
    db.session.delete(user)
    db.session.commit()
    try:
        from services.data_store import export_users
        export_users()
    except Exception:
        pass
    return jsonify({'success': True})


@admin_bp.route('/users/<int:uid>/ban', methods=['POST'])
@login_required
@super_admin_required
def ban_user(uid):
    user = User.query.get_or_404(uid)
    if user.is_admin:
        return jsonify({'success': False, 'error': 'لا يمكن حظر المشرف'})
    user.is_banned = True
    db.session.commit()
    try:
        from services.data_store import export_users
        export_users()
    except Exception:
        pass
    return jsonify({'success': True})


@admin_bp.route('/users/<int:uid>/unban', methods=['POST'])
@login_required
@super_admin_required
def unban_user(uid):
    user = User.query.get_or_404(uid)
    user.is_banned = False
    db.session.commit()
    try:
        from services.data_store import export_users
        export_users()
    except Exception:
        pass
    return jsonify({'success': True})


@admin_bp.route('/users/<int:uid>/promote', methods=['POST'])
@login_required
@super_admin_required
def promote_user(uid):
    from services.email_service import send_promotion_email
    user = User.query.get_or_404(uid)
    data = request.get_json() or {}
    action = data.get('action', 'promote')
    if action == 'demote':
        user.is_admin = False
        user.admin_role = ''
        user.perm_questions = False
        user.perm_users = False
        user.perm_community = False
        user.perm_analytics = False
        user.perm_notifications = False
        user.perm_lectures = False
        user.receive_lecture_notifs = True
        user.receive_exam_notifs = True
        db.session.commit()
    else:
        role = data.get('role', 'مشرف')
        perms = {
            'perm_questions':          bool(data.get('perm_questions')),
            'perm_users':              bool(data.get('perm_users')),
            'perm_community':          bool(data.get('perm_community')),
            'perm_analytics':          bool(data.get('perm_analytics')),
            'perm_notifications':      bool(data.get('perm_notifications')),
            'perm_lectures':           bool(data.get('perm_lectures')),
            'receive_lecture_notifs':  data.get('receive_lecture_notifs', True) not in (False, 'false', 0),
            'receive_exam_notifs':     data.get('receive_exam_notifs',    True) not in (False, 'false', 0),
        }
        user.is_admin              = True
        user.admin_role            = role
        user.perm_questions        = perms['perm_questions']
        user.perm_users            = perms['perm_users']
        user.perm_community        = perms['perm_community']
        user.perm_analytics        = perms['perm_analytics']
        user.perm_notifications    = perms['perm_notifications']
        user.perm_lectures         = perms['perm_lectures']
        user.receive_lecture_notifs = perms['receive_lecture_notifs']
        user.receive_exam_notifs   = perms['receive_exam_notifs']
        db.session.commit()

        # إشعار داخلي في المنصة
        try:
            from models.notification import Notification
            notif = Notification(
                user_id    = user.id,
                sender_id  = current_user.id,
                title      = 'لقد تم ترقيتك إلى مشرف 🎖️',
                body       = f'قام {current_user.name} بترقيتك إلى منصب "{role}" في منصة رواد التحصيلي.',
                notif_type = 'admin',
                link       = '/admin/dashboard',
            )
            db.session.add(notif)
            db.session.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[PROMOTE NOTIF] فشل إنشاء الإشعار: {e}")

        # إرسال بريد إشعار الترقية (اختياري — لا يوقف العملية عند الفشل)
        try:
            dashboard_url = request.host_url.rstrip('/') + '/admin/dashboard'
            send_promotion_email(user.email, user.name, role, perms, dashboard_url)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[PROMOTE EMAIL] فشل إرسال بريد الترقية: {e}")

    return jsonify({'success': True})

@admin_bp.route('/test-email', methods=['POST'])
@login_required
@admin_required
def test_email():
    from services.email_service import _send_email
    to = request.get_json().get('email') or current_user.email
    try:
        _send_email(to, 'اختبار البريد - رواد التحصيلي',
                    '<h2 style="color:#FFB800">✅ البريد الإلكتروني يعمل بنجاح!</h2>'
                    '<p>وصلت هذه الرسالة من منصة رواد التحصيلي.</p>')
        return jsonify({'success': True, 'msg': f'أُرسل بنجاح إلى {to}'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)}), 500


@admin_bp.route('/competitions/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_competition():
    if request.method == 'POST':
        data = request.get_json()
        from services.competition_service import create_competition
        comp = create_competition(data, current_user.id)
        return jsonify({'success': True, 'id': comp.id})
    return render_template('admin_create_competition.html')

# ═══════════════════════════════════════════════════
# استيراد دفعي عبر الكود
# ═══════════════════════════════════════════════════
def _parse_qs_code(code: str) -> list:
    """يحوّل كود JSON أو Python إلى قائمة أسئلة."""
    code = code.strip()
    for start_char in ['[', '{']:
        try:
            idx = code.index(start_char)
            if start_char == '[':
                end_idx = code.rindex(']') + 1
            else:
                end_idx = code.rindex('}') + 1
            chunk = code[idx:end_idx]
            result = json.loads(chunk)
            return result if isinstance(result, list) else [result]
        except Exception:
            pass
    # Python literal eval fallback
    try:
        idx = code.index('[')
        end_idx = code.rindex(']') + 1
        result = ast.literal_eval(code[idx:end_idx])
        return result if isinstance(result, list) else []
    except Exception:
        return []

@admin_bp.route('/questions/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_questions():
    if request.method == 'GET':
        return render_template('admin_import_questions.html')

    data     = request.get_json()
    code     = data.get('code', '').strip()
    subject  = data.get('subject', 'physics')
    grade    = data.get('grade', '3')
    exam_type= data.get('exam_type', 'general')
    diff     = data.get('difficulty', '')

    questions = _parse_qs_code(code)
    if not questions:
        return jsonify({'success': False, 'error': 'لم يتم التعرف على أي أسئلة في الكود'})

    required = {'text', 'option_a', 'option_b', 'option_c', 'option_d', 'answer'}
    valid = []
    skipped = 0
    for q in questions:
        if not required.issubset(q.keys()):
            skipped += 1
            continue
        if 'subject'   not in q: q['subject']   = subject
        if 'grade'     not in q: q['grade']      = grade
        if 'exam_type' not in q: q['exam_type']  = exam_type
        if diff and 'difficulty' not in q: q['difficulty'] = diff
        valid.append(q)

    added = bulk_add_questions(valid, current_user.id)
    try:
        from services.data_store import export_questions
        export_questions()
    except Exception:
        pass
    return jsonify({'success': True, 'added': added,
                    'total': len(questions), 'skipped': skipped})

@admin_bp.route('/questions/ai-fix-code', methods=['POST'])
@login_required
@admin_required
def ai_fix_import_code():
    data = request.get_json()
    code = data.get('code', '')
    if not code.strip():
        return jsonify({'success': False, 'error': 'الكود فارغ'})
    result = fix_import_code(code)
    return jsonify({'success': True, **result})

@admin_bp.route('/questions/preview-code', methods=['POST'])
@login_required
@admin_required
def preview_import_code():
    data = request.get_json()
    code = data.get('code', '')
    questions = _parse_qs_code(code)
    required = {'text', 'option_a', 'option_b', 'option_c', 'option_d', 'answer'}
    valid   = [q for q in questions if required.issubset(q.keys())]
    invalid = len(questions) - len(valid)
    preview = [{'text': q.get('text','')[:80], 'answer': q.get('answer',''),
                'difficulty': q.get('difficulty','medium')} for q in valid[:5]]
    return jsonify({'success': True, 'total': len(questions),
                    'valid': len(valid), 'invalid': invalid, 'preview': preview})

# ═══════════════════════════════════════════════════
# إدارة المشرفين — للمشرف العام فقط
# ═══════════════════════════════════════════════════
@admin_bp.route('/supervisors')
@login_required
@super_admin_required
def supervisors():
    admins = User.query.filter_by(is_admin=True).order_by(User.created_at.asc()).all()
    return render_template('admin_supervisors.html', admins=admins)


@admin_bp.route('/supervisors/search')
@login_required
@super_admin_required
def supervisors_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])
    users = (User.query
             .filter(User.is_admin == False)
             .filter(db.or_(User.name.ilike(f'%{q}%'), User.email.ilike(f'%{q}%')))
             .limit(10).all())
    return jsonify([{'id': u.id, 'name': u.name, 'email': u.email} for u in users])


@admin_bp.route('/supervisors/<int:uid>/update', methods=['POST'])
@login_required
@super_admin_required
def supervisors_update(uid):
    return promote_user(uid)


@admin_bp.route('/seed-questions', methods=['POST'])
@login_required
@admin_required
def seed_questions():
    from data.exams.physics.chapter_1   import QUESTIONS as PH1
    from data.exams.physics.chapter_2   import QUESTIONS as PH2
    from data.exams.chemistry.chapter_1 import QUESTIONS as CH1
    from data.exams.chemistry.chapter_2 import QUESTIONS as CH2
    from data.exams.biology.chapter_1   import QUESTIONS as BI1
    from data.exams.biology.chapter_2   import QUESTIONS as BI2
    from data.exams.math.chapter_1      import QUESTIONS as MA1
    from data.exams.math.chapter_2      import QUESTIONS as MA2

    all_q = PH1 + PH2 + CH1 + CH2 + BI1 + BI2 + MA1 + MA2
    added = bulk_add_questions(all_q, current_user.id)
    try:
        from services.data_store import export_questions
        export_questions()
    except Exception:
        pass
    return jsonify({'success': True, 'added': added})


# ═══════════════════════════════════════════════════════════════════════════
# مفتاح الذكاء الاصطناعي — يُحدَّث من لوحة المشرف
# ═══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/ai-key', methods=['POST'])
@login_required
@super_admin_required
def update_ai_key():
    from flask import current_app
    data = request.get_json(silent=True) or {}
    key  = (data.get('key') or '').strip()
    if not key:
        return jsonify({'success': False, 'error': 'المفتاح فارغ'})
    try:
        from services.data_store import set_ai_key
        set_ai_key(key)
        return jsonify({'success': True, 'msg': 'تم حفظ المفتاح ورفعه إلى GitHub ✅'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@admin_bp.route('/ai-key/current')
@login_required
@super_admin_required
def get_current_ai_key():
    try:
        from services.data_store import get_ai_key
        key = get_ai_key()
        masked = (key[:8] + '****' + key[-4:]) if len(key) > 12 else ('****' if key else 'غير محدد')
        return jsonify({'success': True, 'masked': masked, 'has_key': bool(key)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# مفتاح GitHub
# ═══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/github-token', methods=['POST'])
@login_required
@super_admin_required
def update_github_token():
    data  = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()
    if not token:
        return jsonify({'success': False, 'error': 'التوكن فارغ'})
    try:
        from services.data_store import set_github_token
        set_github_token(token)
        return jsonify({'success': True, 'msg': 'تم حفظ مفتاح GitHub ✅'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@admin_bp.route('/github-token/current')
@login_required
@super_admin_required
def get_current_github_token():
    try:
        from services.data_store import get_github_token
        token = get_github_token()
        masked = ('ghp_' + '****' + token[-4:]) if len(token) > 8 else ('****' if token else 'غير محدد')
        return jsonify({'success': True, 'masked': masked, 'has_token': bool(token)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# تفضيل نموذج الذكاء الاصطناعي
# ═══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/ai-model', methods=['POST'])
@login_required
@super_admin_required
def update_ai_model():
    data     = request.get_json(silent=True) or {}
    model_id = (data.get('model') or 'auto').strip()
    try:
        from services.data_store import set_ai_model_pref
        set_ai_model_pref(model_id)
        return jsonify({'success': True, 'msg': f'تم حفظ إعداد النموذج: {model_id} ✅'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@admin_bp.route('/ai-model/current')
@login_required
@super_admin_required
def get_current_ai_model():
    try:
        from services.data_store import get_ai_model_pref
        return jsonify({'success': True, 'model': get_ai_model_pref()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# تصدير / نسخ احتياطي كامل فوري إلى GitHub
# ═══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/backup/export', methods=['POST'])
@login_required
@super_admin_required
def full_export():
    try:
        from services.data_store import export_all
        export_all()
        return jsonify({'success': True, 'msg': 'تم تصدير المستخدمين والأسئلة والمحاضرات إلى GitHub ✅'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
