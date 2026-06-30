from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models.direct_message import DirectMessage
from models.user import User
from models.notification import Notification
from sqlalchemy import or_, and_

messages_bp = Blueprint('messages', __name__)


# ─── صندوق الوارد للطالب: محادثته مع الأدمن ───────────────────
@messages_bp.route('/')
@login_required
def inbox():
    if current_user.is_admin:
        return redirect(url_for('messages.admin_inbox'))

    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        flash('لا يوجد مشرف في النظام', 'warning')
        return redirect(url_for('student.dashboard'))

    return redirect(url_for('messages.thread', user_id=admin.id))


# ─── خيط المحادثة بين الطالب والأدمن ─────────────────────────
@messages_bp.route('/thread/<int:user_id>', methods=['GET', 'POST'])
@login_required
def thread(user_id):
    # الطالب: user_id هو الأدمن. الأدمن: user_id هو الطالب
    other = User.query.get_or_404(user_id)

    # تحقق صلاحية: طالب يرى أدمن فقط / أدمن يرى أي طالب
    if not current_user.is_admin and not other.is_admin:
        abort(403)
    if current_user.is_admin and other.is_admin:
        abort(403)

    msgs = (DirectMessage.query
            .filter(
                or_(
                    and_(DirectMessage.sender_id == current_user.id,
                         DirectMessage.recipient_id == other.id),
                    and_(DirectMessage.sender_id == other.id,
                         DirectMessage.recipient_id == current_user.id)
                )
            )
            .order_by(DirectMessage.created_at.asc())
            .all())

    # وضع الرسائل الواردة كـ مقروءة
    DirectMessage.query.filter_by(
        sender_id=other.id,
        recipient_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()

    if request.method == 'POST':
        body = request.form.get('body', '').strip()
        if body:
            dm = DirectMessage(
                sender_id=current_user.id,
                recipient_id=other.id,
                body=body
            )
            db.session.add(dm)

            # إشعار للمستلم إذا كان طالباً
            if not other.is_admin:
                notif = Notification(
                    user_id=other.id,
                    sender_id=current_user.id,
                    title=f'رسالة جديدة من المشرف',
                    body=body[:100] + ('…' if len(body) > 100 else ''),
                    notif_type='admin',
                    link=url_for('messages.thread', user_id=current_user.id)
                )
                db.session.add(notif)

            db.session.commit()

        return redirect(url_for('messages.thread', user_id=user_id))

    return render_template('messages_thread.html', other=other, msgs=msgs)


# ─── صندوق الوارد للأدمن: جميع المحادثات ─────────────────────
@messages_bp.route('/admin/inbox')
@login_required
def admin_inbox():
    if not current_user.is_admin:
        abort(403)

    # جلب كل رسائل الأدمن (مُرسَلة أو مُستَقبَلة) مرتبة بالأحدث
    all_msgs = (DirectMessage.query
                .filter(
                    or_(
                        DirectMessage.sender_id == current_user.id,
                        DirectMessage.recipient_id == current_user.id
                    )
                )
                .order_by(DirectMessage.created_at.desc())
                .all())

    # تجميع في Python: آخر رسالة لكل مستخدم
    seen_users = {}
    for m in all_msgs:
        other_id = m.recipient_id if m.sender_id == current_user.id else m.sender_id
        if other_id not in seen_users:
            seen_users[other_id] = m   # أحدث رسالة

    conversations = []
    for other_id, last_msg in seen_users.items():
        other = User.query.get(other_id)
        if not other:
            continue
        unread = DirectMessage.query.filter_by(
            sender_id=other_id,
            recipient_id=current_user.id,
            is_read=False
        ).count()
        conversations.append({'user': other, 'last': last_msg, 'unread': unread})

    # ترتيب: المحادثات التي بها رسائل غير مقروءة أولاً
    conversations.sort(key=lambda x: (-(x['unread'] > 0), -x['last'].id))

    return render_template('admin_inbox.html', conversations=conversations)


# ─── AJAX: عدد الرسائل غير المقروءة ──────────────────────────
@messages_bp.route('/unread-count')
@login_required
def unread_count():
    count = DirectMessage.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({'count': count})
