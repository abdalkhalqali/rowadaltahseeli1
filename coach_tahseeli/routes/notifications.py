from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from extensions import db
from models.notification import Notification
from models.direct_message import DirectMessage
from models.user import User
import logging

notifications_bp = Blueprint('notifications', __name__)

_log = logging.getLogger(__name__)


def notify_admins(title: str, body: str = '', link: str = '',
                  notif_type: str = 'system', filter_key: str = None):
    """يُرسل إشعاراً لجميع المشرفين مع مراعاة تفضيلاتهم."""
    try:
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            if filter_key == 'lecture' and not getattr(admin, 'receive_lecture_notifs', True):
                continue
            if filter_key == 'exam' and not getattr(admin, 'receive_exam_notifs', True):
                continue
            n = Notification(
                user_id=admin.id,
                title=title,
                body=body,
                notif_type=notif_type,
                link=link,
            )
            db.session.add(n)
        db.session.commit()
    except Exception as exc:
        _log.warning(f'[notify_admins] {exc}')


@notifications_bp.route('/')
@login_required
def index():
    notifs = (Notification.query
              .filter_by(user_id=current_user.id)
              .order_by(Notification.created_at.desc())
              .limit(50).all())
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', notifs=notifs)


@notifications_bp.route('/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()
    return jsonify({'count': count})


@notifications_bp.route('/read/<int:nid>', methods=['POST'])
@login_required
def mark_read(nid):
    n = Notification.query.get_or_404(nid)
    if n.user_id == current_user.id:
        n.is_read = True
        db.session.commit()
    return jsonify({'ok': True})


# ── Admin: إرسال إشعار ──────────────────────────────────────
@notifications_bp.route('/admin/send', methods=['GET', 'POST'])
@login_required
def admin_send():
    if not current_user.is_admin:
        flash('غير مصرح', 'danger')
        return redirect(url_for('student.dashboard'))

    users = User.query.filter_by(is_admin=False).order_by(User.name).all()

    if request.method == 'POST':
        title     = request.form.get('title', '').strip()
        body      = request.form.get('body', '').strip()
        target    = request.form.get('target', 'all')      # all | user_id
        user_id   = request.form.get('user_id', '')

        if not title:
            flash('العنوان مطلوب', 'warning')
            return render_template('admin_send_notification.html', users=users)

        if target == 'all':
            recipients = users
        else:
            u = User.query.get(user_id)
            recipients = [u] if u else []

        count = 0
        for u in recipients:
            n = Notification(
                user_id=u.id,
                sender_id=current_user.id,
                title=title,
                body=body,
                notif_type='admin',
                link=url_for('messages.thread', user_id=current_user.id)
            )
            db.session.add(n)
            # إذا كان إرسالاً خاصاً لمستخدم واحد: أنشئ DM أيضاً
            if target != 'all':
                dm = DirectMessage(
                    sender_id=current_user.id,
                    recipient_id=u.id,
                    body=f"{title}\n\n{body}".strip() if body else title,
                )
                db.session.add(dm)
            count += 1
        db.session.commit()

        if target != 'all' and recipients:
            flash(f'تم إرسال الرسالة الخاصة لـ {recipients[0].name}', 'success')
            return redirect(url_for('messages.thread', user_id=recipients[0].id))

        flash(f'تم إرسال الإشعار لـ {count} مستخدم', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin_send_notification.html', users=users)
