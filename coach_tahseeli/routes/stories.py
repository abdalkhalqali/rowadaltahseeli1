import os, uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models.story import Story, StoryView, StoryReaction, REACTION_EMOJIS
from models.user import User
from werkzeug.utils import secure_filename

stories_bp = Blueprint('stories', __name__)

def _get_upload_folder():
    from flask import current_app
    base = current_app.config.get('PERSISTENT_UPLOADS', os.path.join(os.path.dirname(__file__), '..', 'static'))
    return os.path.join(base, 'story_images')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'story_images')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# ── إنشاء حالة ────────────────────────────────────────────────
@stories_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        text  = request.form.get('text', '').strip()
        image = request.files.get('image')
        image_path = None

        if not text and (not image or image.filename == ''):
            flash('يجب إضافة نص أو صورة للحالة', 'warning')
            return redirect(url_for('stories.create'))

        if image and image.filename != '' and _allowed(image.filename):
            folder = _get_upload_folder()
            os.makedirs(folder, exist_ok=True)
            ext      = image.filename.rsplit('.', 1)[1].lower()
            filename = f"story_{uuid.uuid4().hex[:12]}.{ext}"
            image.save(os.path.join(folder, filename))
            image_path = f"/static/story_images/{filename}"

        story = Story(
            user_id    = current_user.id,
            text       = text or None,
            image_path = image_path
        )
        db.session.add(story)
        db.session.commit()
        flash('تم نشر الحالة! ستختفي بعد 24 ساعة ⏰', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('create_story.html')


# ── مشاهدة حالة ───────────────────────────────────────────────
@stories_bp.route('/<int:sid>')
@login_required
def view(sid):
    story = Story.query.get_or_404(sid)

    if not story.is_active:
        flash('هذه الحالة انتهت صلاحيتها', 'warning')
        return redirect(url_for('student.dashboard'))

    if not story.has_viewed(current_user.id) and story.user_id != current_user.id:
        sv = StoryView(story_id=story.id, viewer_id=current_user.id)
        db.session.add(sv)
        db.session.commit()

    viewers = []
    if story.user_id == current_user.id:
        viewers = (StoryView.query
                   .filter_by(story_id=story.id)
                   .order_by(StoryView.viewed_at.desc()).all())

    return render_template('view_story.html', story=story, viewers=viewers)


# ── من شاهد حالتي (JSON) ─────────────────────────────────────
@stories_bp.route('/<int:sid>/viewers')
@login_required
def viewers(sid):
    story = Story.query.get_or_404(sid)
    if story.user_id != current_user.id:
        abort(403)
    data = [{'name': sv.viewer.name, 'at': sv.viewed_at.strftime('%H:%M')}
            for sv in story.views.order_by(StoryView.viewed_at.desc()).all()]
    return jsonify(data)


# ── حذف حالة ─────────────────────────────────────────────────
@stories_bp.route('/<int:sid>/delete', methods=['POST'])
@login_required
def delete(sid):
    story = Story.query.get_or_404(sid)
    if story.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    if story.image_path:
        path = os.path.join(os.path.dirname(__file__), '..', 'static',
                            story.image_path.lstrip('/static/'))
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(story)
    db.session.commit()
    return jsonify({'success': True})


# ── الحالات النشطة (للشريط العلوي) ───────────────────────────
@stories_bp.route('/active-users')
@login_required
def active_users():
    now = datetime.utcnow()
    active = (db.session.query(Story.user_id, db.func.max(Story.id).label('latest'))
              .filter(Story.expires_at > now)
              .group_by(Story.user_id)
              .subquery())
    users_with_stories = (User.query
                          .join(active, User.id == active.c.user_id)
                          .filter(User.id != current_user.id)
                          .all())
    my_stories = Story.query.filter_by(user_id=current_user.id).filter(Story.expires_at > now).count()
    data = {
        'my_stories': my_stories,
        'users': [{'id': u.id, 'name': u.name, 'initial': u.name[0]} for u in users_with_stories]
    }
    return jsonify(data)


# ── تفاعل بالإيموجي ──────────────────────────────────────────
@stories_bp.route('/<int:sid>/react', methods=['POST'])
@login_required
def react(sid):
    story = Story.query.get_or_404(sid)
    if not story.is_active:
        return jsonify({'error': 'expired'}), 400
    emoji = (request.get_json() or {}).get('emoji', '')
    if emoji not in REACTION_EMOJIS:
        return jsonify({'error': 'invalid emoji'}), 400
    existing = StoryReaction.query.filter_by(story_id=sid, user_id=current_user.id).first()
    if existing:
        if existing.emoji == emoji:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'action': 'removed', 'emoji': emoji,
                            'counts': _reaction_counts(sid)})
        existing.emoji = emoji
    else:
        db.session.add(StoryReaction(story_id=sid, user_id=current_user.id, emoji=emoji))
    db.session.commit()
    return jsonify({'action': 'added', 'emoji': emoji, 'counts': _reaction_counts(sid)})

def _reaction_counts(sid):
    rows = (db.session.query(StoryReaction.emoji, db.func.count())
            .filter_by(story_id=sid).group_by(StoryReaction.emoji).all())
    return {e: c for e, c in rows}


# ── قائمة حالات مستخدم معين ──────────────────────────────────
@stories_bp.route('/user/<int:uid>')
@login_required
def user_stories(uid):
    now    = datetime.utcnow()
    user   = User.query.get_or_404(uid)
    stories = (Story.query.filter_by(user_id=uid)
               .filter(Story.expires_at > now)
               .order_by(Story.created_at.asc()).all())
    if not stories:
        flash('لا توجد حالات نشطة لهذا المستخدم', 'info')
        return redirect(url_for('student.dashboard'))
    return render_template('user_stories.html', user=user, stories=stories)
