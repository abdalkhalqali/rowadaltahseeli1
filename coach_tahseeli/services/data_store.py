"""
data_store.py — GitHub كقاعدة بيانات دائمة
============================================
• عند كل تغيير (مستخدم / سؤال / محاضرة) → يُكتب ملف JSON محلياً
  ثم يُرفع إلى GitHub في خلفية (thread) لا يُبطئ الطلب.
• عند كل نشر جديد على Render → يُجلب الملف من GitHub API ثم يُستورد.
• النتيجة: البيانات لا تُحذف أبداً عند النشر.

ملاحظة: data_store/ مستثنى من auto_sync (لا يُلمَس بـ force-push).
         الأسئلة تُقسَّم حسب المادة لتجاوز حد 1MB في GitHub API.
"""

import os, json, logging, threading, base64
from datetime import datetime

# ── مسار مجلد data_store (جذر المشروع) ──────────────────────────────────────
STORE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'data_store')
)
os.makedirs(STORE_DIR, exist_ok=True)

# ── معلومات GitHub ─────────────────────────────────────────────────────────────
GITHUB_REPO = 'abdalkhalqali/rowadaltahseeli1'

# ── ملفات الأسئلة مقسّمة حسب المادة والصف (كل ملف < 900KB بعد Base64) ──────
# كل مادة مقسّمة حسب الصف لضمان عدم تجاوز حد GitHub API (1MB)
QUESTION_FILES = {
    'physics_g1':   'questions_physics_g1.json',    # فيزياء صف 10
    'physics_g2':   'questions_physics_g2.json',    # فيزياء صف 11
    'physics_g3':   'questions_physics_g3.json',    # فيزياء صف 12
    'chemistry_g1': 'questions_chemistry_g1.json',  # كيمياء صف 10
    'chemistry_g2': 'questions_chemistry_g2.json',  # كيمياء صف 11
    'chemistry_g3': 'questions_chemistry_g3.json',  # كيمياء صف 12
    'biology_g1':   'questions_biology_g1.json',    # أحياء صف 10
    'biology_g2':   'questions_biology_g2.json',    # أحياء صف 11
    'biology_g3':   'questions_biology_g3.json',    # أحياء صف 12
    'math_g1':      'questions_math_g1.json',       # رياضيات صف 10
    'math_g2':      'questions_math_g2.json',       # رياضيات صف 11
    'math_g3':      'questions_math_g3.json',       # رياضيات صف 12
    'other':        'questions_other.json',
}

# قفل لمنع تعارض threads عند رفع GitHub (حل 409 race-condition)
_github_lock = threading.Lock()

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# I/O المحلي
# ═════════════════════════════════════════════════════════════════════════════

def _read_local(filename):
    path = os.path.join(STORE_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def _write_local(filename, data):
    os.makedirs(STORE_DIR, exist_ok=True)
    path    = os.path.join(STORE_DIR, filename)
    # بدون indent لتقليل الحجم (أسرع رفعاً إلى GitHub API)
    content = json.dumps(data, ensure_ascii=False, separators=(',', ':'), default=str)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return content

# ═════════════════════════════════════════════════════════════════════════════
# رفع إلى GitHub API (في خلفية)
# ═════════════════════════════════════════════════════════════════════════════

def _push_github(filename, content_str):
    """رفع ملف واحد إلى GitHub عبر API (في خلفية مع lock لمنع race-condition)"""
    def _do():
        with _github_lock:
            _push_github_sync(filename, content_str)
    threading.Thread(target=_do, daemon=True).start()


def _push_github_sync(filename, content_str):
    """رفع متزامن (blocking) — يُعاد المحاولة مرة واحدة عند 409"""
    try:
        import requests as rq
        token = os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', '')
        if not token:
            return
        path    = f'data_store/{filename}'
        headers = {
            'Authorization': f'token {token}',
            'Content-Type':  'application/json',
            'User-Agent':    'RowadTahseeli-DataStore',
        }
        url     = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
        encoded = base64.b64encode(content_str.encode('utf-8')).decode('ascii')

        for attempt in range(3):   # حتى 3 محاولات عند 409
            r   = rq.get(url, headers=headers, timeout=15)
            sha = r.json().get('sha', '') if r.status_code == 200 else ''
            body = {
                'message': f'data-sync: {filename} [{datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC]',
                'content': encoded,
            }
            if sha:
                body['sha'] = sha
            resp = rq.put(url, json=body, headers=headers, timeout=40)
            if resp.status_code in (200, 201):
                logger.info(f'data_store: {filename} → GitHub OK (attempt {attempt+1})')
                return
            elif resp.status_code == 409:
                # SHA تغيّر بين GET و PUT — نعيد المحاولة
                logger.warning(f'data_store: {filename} 409 → retry {attempt+1}')
                import time; time.sleep(1)
            else:
                logger.warning(f'data_store GitHub push {filename}: {resp.status_code} {resp.text[:200]}')
                return
    except Exception as e:
        logger.warning(f'data_store GitHub push {filename}: {e}')


def _fetch_from_github(filename):
    """تحميل ملف من GitHub API وحفظه محلياً — يُستدعى عند بدء التشغيل"""
    try:
        import requests as rq
        token = os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', '')
        if not token:
            return False
        path    = f'data_store/{filename}'
        headers = {
            'Authorization': f'token {token}',
            'User-Agent':    'RowadTahseeli-DataStore',
        }
        url  = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
        resp = rq.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data     = resp.json()
            content  = base64.b64decode(data['content'].replace('\n', ''))
            os.makedirs(STORE_DIR, exist_ok=True)
            local_path = os.path.join(STORE_DIR, filename)
            with open(local_path, 'wb') as f:
                f.write(content)
            logger.info(f'data_store: fetched {filename} from GitHub ({len(content)//1024}KB)')
            return True
        else:
            logger.warning(f'data_store fetch {filename}: HTTP {resp.status_code}')
            return False
    except Exception as e:
        logger.warning(f'data_store fetch {filename}: {e}')
        return False


def _ensure_local(filename):
    """إن كان الملف غائباً محلياً → يُحمَّل من GitHub"""
    path = os.path.join(STORE_DIR, filename)
    if not os.path.exists(path):
        logger.info(f'data_store: {filename} غير موجود محلياً — جارٍ الجلب من GitHub...')
        _fetch_from_github(filename)

# ═════════════════════════════════════════════════════════════════════════════
# تصدير البيانات (يُستدعى بعد كل تعديل)
# ═════════════════════════════════════════════════════════════════════════════

def export_users():
    """تصدير جميع المستخدمين → users.json → GitHub"""
    try:
        from models.user import User
        rows = []
        for u in User.query.all():
            rows.append({
                'id':               u.id,
                'name':             u.name,
                'email':            u.email,
                'password':         u.password,
                'gender':           getattr(u, 'gender', 'unknown'),
                'grade':            u.grade or 'unknown',
                'is_admin':         u.is_admin,
                'is_verified':      u.is_verified,
                'is_banned':        getattr(u, 'is_banned', False),
                'admin_role':       getattr(u, 'admin_role', ''),
                'perm_questions':   getattr(u, 'perm_questions', False),
                'perm_users':       getattr(u, 'perm_users', False),
                'perm_community':   getattr(u, 'perm_community', False),
                'perm_analytics':   getattr(u, 'perm_analytics', False),
                'perm_notifications': getattr(u, 'perm_notifications', False),
                'perm_lectures':    getattr(u, 'perm_lectures', False),
                'bio':              getattr(u, 'bio', ''),
                'total_score':      getattr(u, 'total_score', 0),
                'exams_taken':      getattr(u, 'exams_taken', 0),
                'plain_password':   getattr(u, 'plain_password', ''),
                'created_at':       str(u.created_at) if getattr(u, 'created_at', None) else '',
            })
        content = _write_local('users.json', rows)
        _push_github('users.json', content)
        logger.info(f'data_store: exported {len(rows)} users')
    except Exception as e:
        logger.warning(f'data_store export_users: {e}')


def export_questions():
    """
    تصدير الأسئلة مقسّمة حسب المادة (وللرياضيات حسب الصف).
    كل ملف < 900KB base64 → يمكن رفعه عبر GitHub API مباشرةً.
    """
    try:
        from models.question import Question

        # تجميع — كل مادة تُقسَّم حسب grade
        buckets = {s: [] for s in QUESTION_FILES}
        for q in Question.query.all():
            subj  = (q.subject or 'other').lower().strip()
            grade = getattr(q, 'grade', '') or ''
            grade_suffix = f'_g{grade}' if grade in ('1', '2', '3') else '_g1'
            key = f'{subj}{grade_suffix}'
            if key in buckets:
                bucket = key
            elif subj in buckets:
                bucket = subj
            else:
                bucket = 'other'
            buckets[bucket].append({
                'id':           q.id,
                'text':         q.text,
                'option_a':     q.option_a,
                'option_b':     q.option_b,
                'option_c':     q.option_c,
                'option_d':     q.option_d,
                'answer':       q.answer,
                'subject':      q.subject,
                'difficulty':   q.difficulty,
                'grade':        getattr(q, 'grade', ''),
                'chapter':      getattr(q, 'chapter', ''),
                'lesson':       getattr(q, 'lesson', ''),
                'exam_type':    getattr(q, 'exam_type', 'general'),
                'explanation':  getattr(q, 'explanation', ''),
                'image_path':   q.image_path or '',
                'code_snippet': getattr(q, 'code_snippet', ''),
                'code_type':    getattr(q, 'code_type', 'python'),
                'is_active':    q.is_active,
            })

        total = 0
        for subj, filename in QUESTION_FILES.items():
            rows    = buckets[subj]
            content = _write_local(filename, rows)
            _push_github(filename, content)
            logger.info(f'data_store: exported {len(rows)} {subj} questions')
            total += len(rows)
        logger.info(f'data_store: total {total} questions exported')
    except Exception as e:
        logger.warning(f'data_store export_questions: {e}')


def export_lectures():
    """تصدير جميع المحاضرات → lectures.json → GitHub"""
    try:
        from models.lecture import Lecture
        rows = []
        for l in Lecture.query.all():
            rows.append({
                'id':          l.id,
                'title':       l.title,
                'video_url':   l.video_url or '',
                'branch':      getattr(l, 'branch', 'tahseeli'),
                'subject':     l.subject or '',
                'section':     getattr(l, 'section', 'lectures'),
                'channel':     getattr(l, 'channel', ''),
                'standard':    getattr(l, 'standard', ''),
                'description': getattr(l, 'description', ''),
                'order_num':   getattr(l, 'order_num', 0),
                'views_fake':  getattr(l, 'views_fake', 0),
                'transcript':  getattr(l, 'transcript', ''),
                'is_active':   l.is_active,
            })
        content = _write_local('lectures.json', rows)
        _push_github('lectures.json', content)
        logger.info(f'data_store: exported {len(rows)} lectures')
    except Exception as e:
        logger.warning(f'data_store export_lectures: {e}')


def export_all():
    """تصدير كامل — يُستدعى من زر 'نسخ احتياطي كامل' في لوحة المشرف"""
    export_users()
    export_questions()
    export_lectures()
    return True


# ═════════════════════════════════════════════════════════════════════════════
# استيراد عند بدء التشغيل (إذا كانت قاعدة البيانات فارغة)
# ═════════════════════════════════════════════════════════════════════════════

def restore_if_empty():
    """
    يُستدعى عند start-up — يستورد من JSON إذا كانت القاعدة فارغة.
    إن كانت الملفات غائبة محلياً (Render بعد deploy) → يُحمَّل من GitHub أولاً.
    """
    try:
        from models.user     import User
        from models.question import Question

        users_empty = User.query.filter_by(is_admin=False).count() == 0
        qs_empty    = Question.query.count() == 0

        # تأكد من وجود الملفات محلياً — حمّلها من GitHub إن غابت
        _ensure_local('users.json')
        for fname in QUESTION_FILES.values():
            _ensure_local(fname)
        _ensure_local('lectures.json')

        if users_empty:
            _import_users()
        if qs_empty:
            _import_questions()
        _import_lectures()   # آمن دائماً (يتجاهل الموجودة)
    except Exception as e:
        logger.warning(f'data_store restore_if_empty: {e}')


def _import_users():
    from models.user  import User
    from extensions   import db
    data = _read_local('users.json')
    if not data:
        return
    count = 0
    for u in data:
        if User.query.filter_by(email=u['email']).first():
            continue
        user = User(
            name     = u['name'],
            email    = u['email'],
            password = u['password'],      # مُشفّر مسبقاً
            gender   = u.get('gender', 'unknown'),
            grade    = u.get('grade', 'unknown'),
            is_admin     = u.get('is_admin', False),
            is_verified  = u.get('is_verified', False),
            is_banned    = u.get('is_banned', False),
            admin_role   = u.get('admin_role', ''),
            perm_questions    = u.get('perm_questions', False),
            perm_users        = u.get('perm_users', False),
            perm_community    = u.get('perm_community', False),
            perm_analytics    = u.get('perm_analytics', False),
            perm_notifications= u.get('perm_notifications', False),
            perm_lectures     = u.get('perm_lectures', False),
            bio          = u.get('bio', ''),
            total_score  = u.get('total_score', 0),
            exams_taken  = u.get('exams_taken', 0),
            plain_password = u.get('plain_password', ''),
        )
        db.session.add(user)
        count += 1
    db.session.commit()
    logger.info(f'data_store: restored {count} users')


def _import_questions():
    """استيراد الأسئلة من الملفات المقسّمة حسب المادة"""
    from models.question import Question
    from extensions      import db
    total = 0
    for subj, filename in QUESTION_FILES.items():
        data = _read_local(filename)
        if not data:
            logger.warning(f'data_store: {filename} فارغ أو غير موجود')
            continue
        count = 0
        for q in data:
            question = Question(
                text        = q['text'],
                option_a    = q['option_a'],
                option_b    = q['option_b'],
                option_c    = q['option_c'],
                option_d    = q['option_d'],
                answer      = q['answer'],
                subject     = q['subject'],
                difficulty  = q['difficulty'],
                grade       = q.get('grade', ''),
                chapter     = q.get('chapter', ''),
                lesson      = q.get('lesson', ''),
                exam_type   = q.get('exam_type', 'general'),
                explanation = q.get('explanation', ''),
                image_path  = q.get('image_path', ''),
                code_snippet= q.get('code_snippet', ''),
                code_type   = q.get('code_type', 'python'),
                is_active   = q.get('is_active', True),
                created_by  = 1,
            )
            db.session.add(question)
            count += 1
        db.session.commit()
        logger.info(f'data_store: restored {count} {subj} questions')
        total += count
    logger.info(f'data_store: total {total} questions restored')


def _import_lectures():
    from models.lecture import Lecture
    from extensions     import db
    data = _read_local('lectures.json')
    if not data:
        return
    count = 0
    for l in data:
        exists = Lecture.query.filter_by(
            title=l['title'], subject=l.get('subject', '')
        ).first()
        if exists:
            continue
        lec = Lecture(
            title       = l['title'],
            video_url   = l.get('video_url', ''),
            branch      = l.get('branch', 'tahseeli'),
            subject     = l.get('subject', ''),
            section     = l.get('section', 'lectures'),
            channel     = l.get('channel', ''),
            standard    = l.get('standard', ''),
            description = l.get('description', ''),
            order_num   = l.get('order_num', 0),
            views_fake  = l.get('views_fake', 0),
            transcript  = l.get('transcript', ''),
            is_active   = l.get('is_active', True),
            created_by  = 1,
        )
        db.session.add(lec)
        count += 1
    if count:
        db.session.commit()
        logger.info(f'data_store: restored {count} lectures')


# ═════════════════════════════════════════════════════════════════════════════
# مفتاح الذكاء الاصطناعي
# ═════════════════════════════════════════════════════════════════════════════

def get_ai_key():
    """قراءة مفتاح AI: config.json أولاً ثم متغير البيئة"""
    try:
        cfg = _read_local('config.json') or {}
        key = cfg.get('openrouter_key', '').strip()
        if key:
            return key
    except Exception:
        pass
    return os.getenv('OPENROUTER_KEY', '')


def get_github_token():
    """قراءة مفتاح GitHub: config.json أولاً ثم متغير البيئة"""
    try:
        cfg = _read_local('config.json') or {}
        key = cfg.get('github_token', '').strip()
        if key:
            return key
    except Exception:
        pass
    return os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', '')


def set_github_token(token: str):
    """حفظ مفتاح GitHub في config.json"""
    try:
        _ensure_local('config.json')
        cfg = _read_local('config.json') or {}
        cfg['github_token'] = token.strip()
        cfg['updated_at']   = str(datetime.utcnow())
        _write_local('config.json', cfg)
        # لا نرفع config.json لـ GitHub لأنه يحتوي على token حساس
        return True
    except Exception as e:
        logger.warning(f'data_store set_github_token: {e}')
        return False


def get_ai_model_pref():
    """قراءة تفضيل النموذج المختار لمساعد الطلاب"""
    try:
        cfg = _read_local('config.json') or {}
        return cfg.get('ai_model_pref', 'auto')
    except Exception:
        return 'auto'


def set_ai_model_pref(model_id: str):
    """حفظ تفضيل النموذج في config.json"""
    try:
        _ensure_local('config.json')
        cfg = _read_local('config.json') or {}
        cfg['ai_model_pref'] = model_id
        cfg['updated_at']    = str(datetime.utcnow())
        _write_local('config.json', cfg)
        return True
    except Exception as e:
        logger.warning(f'data_store set_ai_model_pref: {e}')
        return False


def set_ai_key(key: str):
    """حفظ مفتاح AI في config.json ورفعه إلى GitHub"""
    try:
        _ensure_local('config.json')
        cfg = _read_local('config.json') or {}
        cfg['openrouter_key'] = key.strip()
        cfg['updated_at']     = str(datetime.utcnow())
        content = _write_local('config.json', cfg)
        _push_github('config.json', content)
        return True
    except Exception as e:
        logger.warning(f'data_store set_ai_key: {e}')
        return False
