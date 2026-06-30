import os
from flask import Flask, send_from_directory, render_template_string
from extensions import db, login_manager, mail
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'rowad-tahseeli-secret-2025-xK9mP')
    basedir = os.path.abspath(os.path.dirname(__file__))
    # DB_PATH يُستخدم على Render لتخزين البيانات على القرص الدائم /var/data
    db_path = os.getenv('DB_PATH', os.path.join(basedir, 'tahseeli.db'))
    # إنشاء المجلد إن لم يكن موجوداً (مهم عند أول تشغيل على Render)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

    # ── مجلدات الرفع — تُخزَّن على القرص الدائم في Render (/var/data) ──
    # إذا كان DB_PATH يشير إلى /var/data نستخدم نفس القرص لحفظ الملفات
    data_root = os.path.dirname(db_path)  # /var/data على Render، أو مجلد التطبيق محلياً
    persistent_uploads = os.path.join(data_root, 'uploads')

    static_uploads = os.path.join(basedir, 'static', 'uploads')

    # إنشاء مجلدات الرفع الدائمة
    for sub in ('lectures', 'cms', 'question_images', 'story_images'):
        os.makedirs(os.path.join(persistent_uploads, sub), exist_ok=True)

    # إنشاء symlink من static/uploads إلى القرص الدائم (إن لم يكن موجوداً)
    if not os.path.islink(static_uploads) and os.path.isdir(static_uploads):
        # نقل الملفات الموجودة إلى القرص الدائم أولاً
        import shutil
        for sub in os.listdir(static_uploads):
            src = os.path.join(static_uploads, sub)
            dst = os.path.join(persistent_uploads, sub)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
                shutil.rmtree(src)
            elif os.path.isfile(src):
                shutil.copy2(src, dst)
                os.remove(src)
        try:
            os.rmdir(static_uploads)
        except Exception:
            pass
    if not os.path.exists(static_uploads):
        os.symlink(persistent_uploads, static_uploads)

    upload_dir = os.path.join(persistent_uploads, 'lectures')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['LECTURE_UPLOAD_DIR'] = upload_dir
    app.config['PERSISTENT_UPLOADS'] = persistent_uploads

    app.config['MAIL_SERVER']         = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT']           = int(os.getenv('MAIL_PORT', 465))
    app.config['MAIL_USE_TLS']        = False
    app.config['MAIL_USE_SSL']        = True
    app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD', '').replace(' ', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'noreply@rowadtahseeli.sa')

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view     = 'auth.login'
    login_manager.login_message  = 'يرجى تسجيل الدخول أولاً'
    login_manager.login_message_category = 'warning'

    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes import register_blueprints
    register_blueprints(app)

    # ── مسارات PWA ──
    @app.route('/manifest.json')
    def pwa_manifest():
        return send_from_directory('static', 'manifest.json',
                                   mimetype='application/manifest+json')

    @app.route('/sw.js')
    def pwa_sw():
        resp = send_from_directory('static', 'sw.js',
                                   mimetype='application/javascript')
        resp.headers['Service-Worker-Allowed'] = '/'
        return resp

    @app.route('/offline')
    def pwa_offline():
        return render_template_string(OFFLINE_PAGE)

    @app.context_processor
    def inject_notif_count():
        from flask_login import current_user
        try:
            if current_user.is_authenticated:
                from models.notification import Notification
                from models.direct_message import DirectMessage
                notif_count = Notification.query.filter_by(
                    user_id=current_user.id, is_read=False
                ).count()
                dm_count = DirectMessage.query.filter_by(
                    recipient_id=current_user.id, is_read=False
                ).count()
                from routes.admin import SUPER_ADMIN_EMAIL
                return {
                    'unread_notif_count': notif_count,
                    'unread_dm_count': dm_count,
                    'is_super_admin': current_user.email.lower() == SUPER_ADMIN_EMAIL.lower(),
                }
        except Exception:
            pass
        return {'unread_notif_count': 0, 'unread_dm_count': 0, 'is_super_admin': False}

    with app.app_context():
        db.create_all()
        _run_migrations()
        _seed_admin()
        # استعادة البيانات من GitHub إن كانت قاعدة البيانات فارغة
        try:
            from services.data_store import restore_if_empty
            restore_if_empty()
        except Exception as _ds_err:
            import logging
            logging.warning(f'data_store restore: {_ds_err}')

    return app

OFFLINE_PAGE = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>بدون إنترنت — رواد التحصيلي</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#080b14;color:#e2e8f0;font-family:system-ui,sans-serif;
    display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:2rem}
  .card{background:#141824;border:1px solid #2a2f3e;border-radius:20px;padding:3rem 2rem;max-width:400px;width:100%}
  .icon{font-size:4rem;margin-bottom:1rem}
  h1{font-size:1.5rem;margin-bottom:.75rem;color:#fff}
  p{color:#94a3b8;margin-bottom:1.5rem;line-height:1.6}
  button{background:#6366f1;color:#fff;border:none;border-radius:10px;
    padding:.75rem 2rem;font-size:1rem;cursor:pointer;font-family:inherit}
  button:hover{background:#5558e0}
</style>
</head>
<body>
<div class="card">
  <div class="icon">📡</div>
  <h1>لا يوجد اتصال بالإنترنت</h1>
  <p>يبدو أنك غير متصل بالإنترنت. تحقق من اتصالك وحاول مجدداً.</p>
  <button onclick="location.reload()">إعادة المحاولة</button>
</div>
</body>
</html>'''

def _run_migrations():
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN admin_role VARCHAR(30) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN perm_questions BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN perm_users BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN perm_community BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN perm_analytics BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN perm_notifications BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN perm_lectures BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN receive_lecture_notifs BOOLEAN DEFAULT 1",
        "ALTER TABLE users ADD COLUMN receive_exam_notifs BOOLEAN DEFAULT 1",
        """CREATE TABLE IF NOT EXISTS story_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL REFERENCES stories(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            emoji VARCHAR(10) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_id, user_id)
        )""",
        "ALTER TABLE notifications ADD COLUMN sender_id INTEGER REFERENCES users(id)",
        "ALTER TABLE notifications ADD COLUMN link VARCHAR(200) DEFAULT ''",
        "ALTER TABLE lectures ADD COLUMN views_real INTEGER DEFAULT 0",
        "ALTER TABLE lectures ADD COLUMN views_fake INTEGER DEFAULT 0",
        """CREATE TABLE IF NOT EXISTS lecture_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL REFERENCES lectures(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            learned TEXT DEFAULT '',
            needs_clarification TEXT DEFAULT '',
            rating INTEGER DEFAULT 5,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        "ALTER TABLE lectures ADD COLUMN transcript TEXT DEFAULT ''",
        "ALTER TABLE pro_license_results ADD COLUMN exam_type VARCHAR(20) DEFAULT 'standard'",
        "ALTER TABLE pro_license_questions ADD COLUMN has_drawing BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN plain_password VARCHAR(256)",
        "ALTER TABLE questions ADD COLUMN code_snippet TEXT DEFAULT ''",
        "ALTER TABLE questions ADD COLUMN code_type VARCHAR(20) DEFAULT 'python'",
        "ALTER TABLE pro_license_questions ADD COLUMN code_snippet TEXT DEFAULT ''",
        "ALTER TABLE pro_license_questions ADD COLUMN code_type VARCHAR(20) DEFAULT 'python'",
        """CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            role VARCHAR(20) DEFAULT 'user',
            content TEXT NOT NULL,
            lecture_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS daily_training_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            day_num INTEGER DEFAULT 1,
            exam_date DATE,
            questions_ids TEXT DEFAULT '[]',
            review_ids TEXT DEFAULT '[]',
            wrong_ids TEXT DEFAULT '[]',
            score INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            completed BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS cms_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            icon VARCHAR(10) DEFAULT '📁',
            parent_id INTEGER REFERENCES cms_sections(id),
            order_num INTEGER DEFAULT 0,
            link VARCHAR(500) DEFAULT '',
            fallback_msg TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS cms_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(300) NOT NULL,
            section_id INTEGER REFERENCES cms_sections(id),
            file_path VARCHAR(500) DEFAULT '',
            file_url VARCHAR(500) DEFAULT '',
            file_type VARCHAR(20) DEFAULT 'pdf',
            file_size INTEGER DEFAULT 0,
            ai_topic VARCHAR(200) DEFAULT '',
            ai_keywords TEXT DEFAULT '',
            ai_summary TEXT DEFAULT '',
            ai_difficulty VARCHAR(30) DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
        )""",
        """CREATE TABLE IF NOT EXISTS cms_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(300) NOT NULL,
            section_id INTEGER REFERENCES cms_sections(id),
            code_type VARCHAR(20) DEFAULT 'python',
            difficulty VARCHAR(20) DEFAULT 'medium',
            description TEXT DEFAULT '',
            code_content TEXT DEFAULT '',
            external_url VARCHAR(500) DEFAULT '',
            questions_json TEXT DEFAULT '[]',
            ai_topic VARCHAR(200) DEFAULT '',
            ai_keywords TEXT DEFAULT '',
            ai_summary TEXT DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
        )""",
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass

def _seed_admin():
    from models.user import User
    from werkzeug.security import generate_password_hash
    
    # قائمة المشرفين (أدخل بريدك الإلكتروني وكلمة المرور هنا)
    admins_to_create = [
        {
            'name': 'المشرف الأول',
            'email': 'admin@rowadtahseeli.sa',    # 👈 ضع البريد الإلكتروني هنا
            'password': 'Admin@2025',         # 👈 ضع كلمة المرور هنا
        },
        {
            'name': 'المشرف الثاني',
            'email': 'admin2@example.com',    # 👈 ضع البريد الإلكتروني هنا
            'password': 'password456',         # 👈 ضع كلمة المرور هنا
        },
        {
            'name': 'المشرف الثالث',
            'email': 'admin3@fatim.com',    # 👈 ضع البريد الإلكتروني هنا
            'password': '507195981f',         # 👈 ضع كلمة المرور هنا
        }
    ]
    
    for admin_data in admins_to_create:
        # التحقق من عدم وجود مشرف بنفس البريد الإلكتروني
        existing_admin = User.query.filter_by(email=admin_data['email']).first()
        if not existing_admin:
            admin = User(
                name=admin_data['name'],
                email=admin_data['email'],
                password=generate_password_hash(admin_data['password']),
                is_admin=True,
                is_verified=True,
                admin_role='super_admin',
                perm_questions=True,
                perm_users=True,
                perm_community=True,
                perm_analytics=True,
                perm_notifications=True,
                is_banned=False,
                bio=''
            )
            db.session.add(admin)
    
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=False)
