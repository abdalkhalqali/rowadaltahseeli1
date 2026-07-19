from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.community import CommunityPost
from models.user import User

community_bp = Blueprint('community', __name__)


@community_bp.route('/')
@login_required
def index():
    tab   = request.args.get('tab', 'general')
    posts = (CommunityPost.query
             .filter_by(is_deleted=False, parent_id=None)
             .order_by(CommunityPost.is_pinned.desc(),
                       CommunityPost.created_at.desc())
             .limit(60).all())
    return render_template('community.html', posts=posts, tab=tab)


@community_bp.route('/post', methods=['POST'])
@login_required
def post():
    body      = request.form.get('body', '').strip()
    post_type = request.form.get('post_type', 'general')
    if not body:
        flash('لا يمكن إرسال رسالة فارغة', 'warning')
        return redirect(url_for('community.index'))
    if len(body) > 1000:
        flash('الرسالة طويلة جداً (الحد 1000 حرف)', 'warning')
        return redirect(url_for('community.index'))
    if post_type not in ('general', 'question', 'achievement'):
        post_type = 'general'
    p = CommunityPost(user_id=current_user.id, body=body, post_type=post_type)
    db.session.add(p)
    db.session.commit()
    return redirect(url_for('community.index'))


@community_bp.route('/reply/<int:post_id>', methods=['POST'])
@login_required
def reply(post_id):
    parent = CommunityPost.query.get_or_404(post_id)
    body   = request.form.get('body', '').strip()
    if not body or len(body) > 500:
        return redirect(url_for('community.index'))
    r = CommunityPost(user_id=current_user.id, body=body,
                      parent_id=parent.id, post_type='reply')
    db.session.add(r)
    db.session.commit()
    return redirect(url_for('community.index'))


@community_bp.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    p = CommunityPost.query.get_or_404(post_id)
    p.likes += 1
    db.session.commit()
    return jsonify({'likes': p.likes})


@community_bp.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete(post_id):
    p = CommunityPost.query.get_or_404(post_id)
    if p.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'unauthorized'}), 403
    p.is_deleted = True
    db.session.commit()
    return jsonify({'ok': True})


@community_bp.route('/pin/<int:post_id>', methods=['POST'])
@login_required
def pin(post_id):
    if not current_user.is_admin:
        return jsonify({'error': 'unauthorized'}), 403
    p = CommunityPost.query.get_or_404(post_id)
    p.is_pinned = not p.is_pinned
    db.session.commit()
    return jsonify({'pinned': p.is_pinned})


@community_bp.route('/api/recent')
@login_required
def api_recent():
    posts = (CommunityPost.query
             .filter_by(is_deleted=False, parent_id=None)
             .order_by(CommunityPost.is_pinned.desc(),
                       CommunityPost.created_at.desc())
             .limit(5).all())
    result = []
    for p in posts:
        u = User.query.get(p.user_id)
        result.append({
            'id':      p.id,
            'name':    u.name if u else 'مجهول',
            'initial': u.name[0] if u else '?',
            'body':    p.body[:120] + ('…' if len(p.body) > 120 else ''),
            'type':    p.post_type,
            'likes':   p.likes,
            'pinned':  p.is_pinned,
            'replies': p.reply_count,
            'time':    p.created_at.strftime('%H:%M'),
            'is_me':   p.user_id == current_user.id,
            'is_admin': u.is_admin if u else False,
        })
    return jsonify(result)
