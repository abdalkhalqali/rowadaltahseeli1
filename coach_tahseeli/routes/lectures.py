from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models.lecture import Lecture, LectureFeedback, LectureView
from models.notification import Notification
from models.user import User
import os, uuid

lectures_bp = Blueprint('lectures', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('هذه الصفحة للمشرفين فقط', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

ALLOWED_VIDEO = {'mp4', 'webm', 'mkv', 'mov', 'avi', 'm4v'}

def _save_uploaded_video(file_obj):
    """يحفظ الفيديو المرفوع ويعيد مسار URL نسبي جاهز للتخزين في video_url"""
    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_VIDEO:
        return None, 'صيغة الملف غير مدعومة — المسموح بها: mp4, webm, mkv, mov, avi'
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config.get('LECTURE_UPLOAD_DIR',
                   os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'lectures'))
    os.makedirs(upload_dir, exist_ok=True)
    file_obj.save(os.path.join(upload_dir, filename))
    return f'/static/uploads/lectures/{filename}', None

SUBJECTS_AR = {
    'physics':   'الفيزياء',
    'chemistry': 'الكيمياء',
    'biology':   'الأحياء',
    'math':      'الرياضيات',
    'general':   'عام',
    'professional_physics': 'فيزياء الرخصة المهنية',
}

SECTIONS_AR = {
    'lectures':       'المحاضرات',
    'exams':          'الاختبارات',
    'daily_training': 'التدريب اليومي',
}

def _broadcast_notification(title, body, link='', notif_type='admin'):
    try:
        students = User.query.filter_by(is_admin=False).all()
        for s in students:
            n = Notification(
                user_id    = s.id,
                sender_id  = current_user.id,
                title      = title,
                body       = body,
                notif_type = notif_type,
                link       = link,
            )
            db.session.add(n)
        db.session.commit()
    except Exception as e:
        print(f'Notification error: {e}')

# ─── لوحة المالك ────────────────────────────────────────────
@lectures_bp.route('/admin/lectures')
@login_required
@admin_required
def admin_lectures():
    branch  = request.args.get('branch', 'tahseeli')
    section = request.args.get('section', '')
    subject = request.args.get('subject', '')

    q = Lecture.query.filter_by(is_active=True, branch=branch)
    if section:
        q = q.filter_by(section=section)
    if subject:
        q = q.filter_by(subject=subject)

    lectures = q.order_by(Lecture.order_num.asc(), Lecture.created_at.desc()).all()
    return render_template('admin_lectures.html',
                           lectures=lectures,
                           branch=branch,
                           section=section,
                           subject=subject,
                           subjects_ar=SUBJECTS_AR,
                           sections_ar=SECTIONS_AR)

@lectures_bp.route('/admin/lectures/add', methods=['POST'])
@login_required
@admin_required
def admin_add_lecture():
    branch = request.form.get('branch', 'tahseeli')

    # تحديد مصدر الفيديو: ملف مرفوع أم رابط
    video_url = request.form.get('video_url', '').strip()
    uploaded  = request.files.get('video_file')
    if uploaded and uploaded.filename:
        saved_url, err = _save_uploaded_video(uploaded)
        if err:
            flash(err, 'danger')
            return redirect(url_for('lectures.admin_lectures', branch=branch))
        video_url = saved_url

    if not video_url:
        flash('يجب إدخال رابط الفيديو أو رفع ملف', 'danger')
        return redirect(url_for('lectures.admin_lectures', branch=branch))

    lec = Lecture(
        title       = request.form.get('title', '').strip(),
        channel     = request.form.get('channel', '').strip(),
        video_url   = video_url,
        description = request.form.get('description', '').strip(),
        standard    = request.form.get('standard', '').strip(),
        subject     = request.form.get('subject', '').strip(),
        branch      = branch,
        section     = request.form.get('section', '').strip(),
        order_num   = int(request.form.get('order_num', 0) or 0),
        views_fake  = int(request.form.get('views_fake', 0) or 0),
        transcript  = request.form.get('transcript', '').strip(),
        created_by  = current_user.id,
    )
    db.session.add(lec)
    db.session.commit()
    try:
        from services.data_store import export_lectures
        export_lectures()
    except Exception:
        pass

    branch_ar = 'التحصيلي' if branch == 'tahseeli' else 'الرخصة المهنية'
    _broadcast_notification(
        title = f'🎬 محاضرة جديدة — {lec.title}',
        body  = f'تمت إضافة محاضرة جديدة في {branch_ar}. يمكنك مشاهدتها الآن!',
        link  = url_for('lectures.watch_lecture', lid=lec.id),
        notif_type='admin',
    )

    _auto_sync(f'إضافة محاضرة: {lec.title}')
    flash('تمت إضافة المحاضرة وإرسال الإشعارات ✅', 'success')
    return redirect(url_for('lectures.admin_lectures', branch=branch))

@lectures_bp.route('/admin/lectures/edit/<int:lid>', methods=['POST'])
@login_required
@admin_required
def admin_edit_lecture(lid):
    lec = Lecture.query.get_or_404(lid)
    lec.title       = request.form.get('title', lec.title).strip()
    lec.channel     = request.form.get('channel', lec.channel or '').strip()
    lec.description = request.form.get('description', lec.description or '').strip()
    lec.standard    = request.form.get('standard', lec.standard or '').strip()
    lec.subject     = request.form.get('subject', lec.subject or '').strip()
    lec.section     = request.form.get('section', lec.section or '').strip()
    lec.order_num   = int(request.form.get('order_num', lec.order_num) or 0)
    fake_val = request.form.get('views_fake')
    if fake_val is not None and fake_val.strip() != '':
        lec.views_fake = int(fake_val or 0)
    lec.transcript = request.form.get('transcript', lec.transcript or '').strip()

    # الفيديو: ملف مرفوع جديد أم الرابط المكتوب أم يُبقى القديم
    uploaded = request.files.get('video_file')
    if uploaded and uploaded.filename:
        saved_url, err = _save_uploaded_video(uploaded)
        if err:
            flash(err, 'danger')
            return redirect(url_for('lectures.admin_lectures', branch=lec.branch))
        lec.video_url = saved_url
    else:
        new_url = request.form.get('video_url', '').strip()
        if new_url:
            lec.video_url = new_url

    db.session.commit()
    try:
        from services.data_store import export_lectures
        export_lectures()
    except Exception:
        pass
    _auto_sync(f'تعديل محاضرة: {lec.title}')
    flash('تم تحديث المحاضرة ✅', 'success')
    return redirect(url_for('lectures.admin_lectures', branch=lec.branch))

@lectures_bp.route('/admin/lectures/delete/<int:lid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_lecture(lid):
    lec = Lecture.query.get_or_404(lid)
    branch = lec.branch
    lec.is_active = False
    db.session.commit()
    try:
        from services.data_store import export_lectures
        export_lectures()
    except Exception:
        pass
    _auto_sync(f'حذف محاضرة: {lec.title}')
    flash('تم حذف المحاضرة ✅', 'success')
    return redirect(url_for('lectures.admin_lectures', branch=branch))

@lectures_bp.route('/admin/lectures/feedbacks/<int:lid>')
@login_required
@admin_required
def admin_lecture_feedbacks(lid):
    lec = Lecture.query.get_or_404(lid)
    feedbacks = LectureFeedback.query.filter_by(lecture_id=lid)\
        .order_by(LectureFeedback.created_at.desc()).all()
    return render_template('admin_lecture_feedbacks.html', lec=lec, feedbacks=feedbacks)

# ─── لوحة الطالب ────────────────────────────────────────────
@lectures_bp.route('/student/lectures')
@login_required
def student_lectures():
    branch  = request.args.get('branch', 'tahseeli')
    section = request.args.get('section', '')
    subject = request.args.get('subject', '')

    q = Lecture.query.filter_by(is_active=True, branch=branch)
    if section:
        q = q.filter_by(section=section)
    if subject:
        q = q.filter_by(subject=subject)

    lectures = q.order_by(Lecture.order_num.asc(), Lecture.created_at.desc()).all()
    return render_template('student_lectures.html',
                           lectures=lectures,
                           branch=branch,
                           section=section,
                           subject=subject,
                           subjects_ar=SUBJECTS_AR,
                           sections_ar=SECTIONS_AR)

@lectures_bp.route('/student/lectures/watch/<int:lid>')
@login_required
def watch_lecture(lid):
    lec = Lecture.query.filter_by(id=lid, is_active=True).first_or_404()

    # تسجيل مشاهدة حقيقية
    lec.views_real = (lec.views_real or 0) + 1

    # تسجيل/تحديث سجل مشاهدة المستخدم
    from datetime import datetime
    view = LectureView.query.filter_by(lecture_id=lid, user_id=current_user.id).first()
    first_open = view is None
    if not view:
        view = LectureView(lecture_id=lid, user_id=current_user.id)
        db.session.add(view)
    view.last_seen = datetime.utcnow()
    db.session.commit()

    # إشعار المشرفين عند أول فتح للمحاضرة من قِبَل الطالب
    if first_open and not current_user.is_admin:
        try:
            from routes.notifications import notify_admins
            subj_ar = SUBJECTS_AR.get(lec.subject or '', lec.subject or '')
            notify_admins(
                title=f'📺 {current_user.name} فتح محاضرة',
                body=(f'الطالب «{current_user.name}» فتح المحاضرة:\n'
                      f'"{lec.title}"\n'
                      f'المادة: {subj_ar}'),
                link=f'/student/lectures/watch/{lid}',
                notif_type='system',
                filter_key='lecture',
            )
        except Exception:
            pass

    related = Lecture.query.filter_by(
        branch=lec.branch, subject=lec.subject, is_active=True
    ).filter(Lecture.id != lid).order_by(Lecture.order_num.asc()).limit(6).all()

    # هل أرسل الطالب ملاحظات من قبل؟
    existing_feedback = LectureFeedback.query.filter_by(
        lecture_id=lid, user_id=current_user.id
    ).first()

    return render_template('watch_lecture.html',
                           lec=lec,
                           related=related,
                           existing_feedback=existing_feedback,
                           subjects_ar=SUBJECTS_AR,
                           sections_ar=SECTIONS_AR,
                           user_view=view)


# ─── API: نبضة تتبع التقدم ────────────────────────────────────
@lectures_bp.route('/api/lecture/heartbeat', methods=['POST'])
@login_required
def lecture_heartbeat():
    from datetime import datetime
    data  = request.get_json(silent=True) or {}
    lid   = data.get('lecture_id')
    secs  = int(data.get('watch_secs', 0) or 0)
    done  = bool(data.get('completed', False))
    if not lid:
        return jsonify({'ok': False}), 400
    view = LectureView.query.filter_by(lecture_id=lid, user_id=current_user.id).first()
    if not view:
        view = LectureView(lecture_id=lid, user_id=current_user.id)
        db.session.add(view)
    # نراكم الثواني فقط إن كانت أكبر من القيمة الحالية
    if secs > (view.watch_secs or 0):
        view.watch_secs = secs
    if done:
        view.completed = True
    view.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'watch_secs': view.watch_secs})

@lectures_bp.route('/student/lectures/feedback/<int:lid>', methods=['POST'])
@login_required
def submit_feedback(lid):
    lec = Lecture.query.filter_by(id=lid, is_active=True).first_or_404()

    existing = LectureFeedback.query.filter_by(
        lecture_id=lid, user_id=current_user.id
    ).first()

    if existing:
        existing.learned             = request.form.get('learned', '').strip()
        existing.needs_clarification = request.form.get('needs_clarification', '').strip()
        existing.rating              = int(request.form.get('rating', 5) or 5)
    else:
        fb = LectureFeedback(
            lecture_id          = lid,
            user_id             = current_user.id,
            learned             = request.form.get('learned', '').strip(),
            needs_clarification = request.form.get('needs_clarification', '').strip(),
            rating              = int(request.form.get('rating', 5) or 5),
        )
        db.session.add(fb)

    db.session.commit()
    flash('تم إرسال ملاحظاتك شكراً لك 🙏', 'success')
    return redirect(url_for('lectures.watch_lecture', lid=lid))

# ─── API: تفريغ قطعة صوتية (WAV base64) من صوت الفيديو ─────
@lectures_bp.route('/api/lecture/transcribe-chunk', methods=['POST'])
@login_required
def transcribe_chunk():
    if not current_user.is_admin:
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    import base64, io
    data      = request.get_json(silent=True) or {}
    audio_b64 = data.get('audio', '')
    if not audio_b64:
        return jsonify({'ok': False, 'error': 'no audio'}), 400
    try:
        audio_bytes = base64.b64decode(audio_b64)
        import speech_recognition as sr
        r    = sr.Recognizer()
        r.energy_threshold    = 300
        r.dynamic_energy_threshold = True
        af   = sr.AudioFile(io.BytesIO(audio_bytes))
        with af as source:
            audio_data = r.record(source)
        text = r.recognize_google(audio_data, language='ar-SA')
        return jsonify({'ok': True, 'text': text})
    except Exception as e:
        err = str(e)
        if 'UnknownValueError' in type(e).__name__ or 'Could not understand' in err:
            return jsonify({'ok': True, 'text': ''})
        return jsonify({'ok': False, 'error': err})


# ─── API: حفظ نص التفريغ الصوتي ────────────────────────────
@lectures_bp.route('/api/lecture/save-transcript', methods=['POST'])
@login_required
def save_transcript():
    if not current_user.is_admin:
        return jsonify({'ok': False, 'error': 'غير مصرح'}), 403
    data = request.get_json(silent=True) or {}
    lid  = data.get('lecture_id')
    text = (data.get('transcript') or '').strip()
    if not lid or not text:
        return jsonify({'ok': False, 'error': 'بيانات ناقصة'}), 400
    lec = Lecture.query.filter_by(id=lid, is_active=True).first_or_404()
    lec.transcript = text
    db.session.commit()
    _auto_sync(f'تحديث نص محاضرة: {lec.title}')
    return jsonify({'ok': True})

# ─── مزامنة GitHub تلقائية ─────────────────────────────────
def _auto_sync(message='تحديث تلقائي'):
    import subprocess, os
    token = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN', '')
    if not token:
        return
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        env  = {**os.environ, 'GIT_ASKPASS': 'echo', 'GIT_TERMINAL_PROMPT': '0'}
        subprocess.run(['git', 'add', '-A'], cwd=root, env=env, timeout=15)
        subprocess.run(['git', 'commit', '-m', message, '--allow-empty'],
                       cwd=root, env=env, timeout=15)
        subprocess.run(['git', 'push'], cwd=root, env=env, timeout=30)
    except Exception:
        pass
