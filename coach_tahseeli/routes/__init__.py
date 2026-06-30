from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.ai import ai_bp
from routes.competition import competition_bp
from routes.community import community_bp
from routes.notifications import notifications_bp
from routes.messages import messages_bp
from routes.stories import stories_bp
from routes.bot_api import bot_api_bp
from routes.lectures import lectures_bp
from routes.pro_license import pro_license_bp
from routes.chat import chat_bp
from routes.cms import cms_bp
from routes.code_assistant import code_assistant_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp,           url_prefix='/auth')
    app.register_blueprint(student_bp,        url_prefix='/student')
    app.register_blueprint(admin_bp,          url_prefix='/admin')
    app.register_blueprint(ai_bp,             url_prefix='/ai')
    app.register_blueprint(competition_bp,    url_prefix='/competition')
    app.register_blueprint(community_bp,      url_prefix='/community')
    app.register_blueprint(notifications_bp,  url_prefix='/notifications')
    app.register_blueprint(messages_bp,       url_prefix='/messages')
    app.register_blueprint(stories_bp,        url_prefix='/stories')
    app.register_blueprint(bot_api_bp,        url_prefix='/api/bot')
    app.register_blueprint(lectures_bp)
    app.register_blueprint(pro_license_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(cms_bp)
    app.register_blueprint(code_assistant_bp)

    from flask import render_template, redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))
