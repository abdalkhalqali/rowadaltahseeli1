from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models.pro_license_question import ProLicenseQuestion, ProLicenseResult, DailyTrainingSession, PRO_STANDARDS
from models.notification import Notification
from models.user import User
from datetime import date
import json, random, ast

pro_license_bp = Blueprint('pro_license', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('هذه الصفحة للمشرفين فقط', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

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

# ─────────────────────────────────────────────
# لوحة المشرف — قائمة الأسئلة
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license')
@login_required
@admin_required
def admin_index():
    standard   = request.args.get('standard', type=int)
    q_type     = request.args.get('type', '')
    difficulty = request.args.get('difficulty', '')

    query = ProLicenseQuestion.query.filter_by(is_active=True)
    if standard:
        query = query.filter_by(standard_num=standard)
    if q_type:
        query = query.filter_by(q_type=q_type)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)

    questions = query.order_by(ProLicenseQuestion.standard_num, ProLicenseQuestion.created_at).all()

    stats = {}
    for s_num, s_info in PRO_STANDARDS.items():
        cnt = ProLicenseQuestion.query.filter_by(standard_num=s_num, is_active=True).count()
        stats[s_num] = {'name': s_info['name'], 'type': s_info['type'], 'count': cnt}

    return render_template('admin_pro_license.html',
        questions=questions,
        standards=PRO_STANDARDS,
        stats=stats,
        selected_standard=standard,
        selected_type=q_type,
        selected_difficulty=difficulty,
    )

# ─────────────────────────────────────────────
# إضافة سؤال
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add():
    if request.method == 'POST':
        std_num  = int(request.form.get('standard_num', 1))
        std_info = PRO_STANDARDS.get(std_num, {})
        q = ProLicenseQuestion(
            text         = request.form.get('text', '').strip(),
            option_a     = request.form.get('option_a', '').strip(),
            option_b     = request.form.get('option_b', '').strip(),
            option_c     = request.form.get('option_c', '').strip(),
            option_d     = request.form.get('option_d', '').strip(),
            answer       = request.form.get('answer', 'A').upper(),
            explanation  = request.form.get('explanation', '').strip(),
            standard_num = std_num,
            standard_name= std_info.get('name', ''),
            q_type       = std_info.get('type', 'educational'),
            difficulty   = request.form.get('difficulty', 'medium'),
            image_data   = request.form.get('image_data', ''),
            code_snippet = request.form.get('code_snippet', ''),
            code_type    = request.form.get('code_type', 'python'),
            created_by   = current_user.id,
        )
        db.session.add(q)
        db.session.commit()
        _broadcast_notification(
            title=f'📚 سؤال جديد — {std_info.get("name","الرخصة المهنية")}',
            body =f'تمت إضافة سؤال جديد في معيار: {std_info.get("name","")} (مستوى: {q.difficulty})',
            link ='/student/pro-license',
        )
        flash('تمت إضافة السؤال وإرسال الإشعارات ✅', 'success')
        return redirect(url_for('pro_license.admin_index', standard=std_num))
    return render_template('admin_pro_license_form.html',
        standards=PRO_STANDARDS, question=None, action='add')

# ─────────────────────────────────────────────
# تعديل سؤال
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license/edit/<int:qid>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit(qid):
    q = ProLicenseQuestion.query.get_or_404(qid)
    if request.method == 'POST':
        std_num       = int(request.form.get('standard_num', q.standard_num))
        std_info      = PRO_STANDARDS.get(std_num, {})
        q.text        = request.form.get('text', q.text).strip()
        q.option_a    = request.form.get('option_a', q.option_a).strip()
        q.option_b    = request.form.get('option_b', q.option_b).strip()
        q.option_c    = request.form.get('option_c', q.option_c).strip()
        q.option_d    = request.form.get('option_d', q.option_d).strip()
        q.answer      = request.form.get('answer', q.answer).upper()
        q.explanation = request.form.get('explanation', q.explanation).strip()
        q.standard_num  = std_num
        q.standard_name = std_info.get('name', q.standard_name)
        q.q_type        = std_info.get('type', q.q_type)
        q.difficulty    = request.form.get('difficulty', q.difficulty)
        new_img = request.form.get('image_data', '')
        if new_img:
            q.image_data = new_img
        q.code_snippet = request.form.get('code_snippet', q.code_snippet or '')
        q.code_type    = request.form.get('code_type',    q.code_type    or 'python')
        db.session.commit()
        flash('تم تعديل السؤال ✅', 'success')
        return redirect(url_for('pro_license.admin_index', standard=std_num))
    return render_template('admin_pro_license_form.html',
        standards=PRO_STANDARDS, question=q, action='edit')

# ─────────────────────────────────────────────
# حذف سؤال
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license/delete/<int:qid>', methods=['POST'])
@login_required
@admin_required
def admin_delete(qid):
    q = ProLicenseQuestion.query.get_or_404(qid)
    std = q.standard_num
    q.is_active = False
    db.session.commit()
    flash('تم حذف السؤال', 'warning')
    return redirect(url_for('pro_license.admin_index', standard=std))

# ─────────────────────────────────────────────
# API: جلب سؤال بصيغة JSON (للتعديل السريع)
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license/api/<int:qid>')
@login_required
@admin_required
def admin_api_question(qid):
    q = ProLicenseQuestion.query.get_or_404(qid)
    return jsonify({
        'id':          q.id,
        'text':        q.text,
        'option_a':    q.option_a,
        'option_b':    q.option_b,
        'option_c':    q.option_c,
        'option_d':    q.option_d,
        'answer':      q.answer,
        'explanation': q.explanation or '',
        'standard_num':q.standard_num,
        'difficulty':  q.difficulty,
        'q_type':      q.q_type,
        'image_data':  q.image_data or '',
    })

# ─────────────────────────────────────────────
# بذر الأسئلة
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license/seed', methods=['POST'])
@login_required
@admin_required
def admin_seed():
    try:
        from data.pro_license_seed import seed_pro_license_questions
        msg = seed_pro_license_questions()
        flash(msg, 'success')
    except Exception as e:
        flash(f'خطأ أثناء البذر: {e}', 'danger')
    return redirect(url_for('pro_license.admin_index'))


@pro_license_bp.route('/admin/pro-license/reshuffle', methods=['POST'])
@login_required
@admin_required
def admin_reshuffle():
    """إعادة خلط خيارات الأسئلة الموجودة لتوزيع الإجابات الصحيحة عشوائياً"""
    try:
        from data.pro_license_seed import reshuffle_existing_questions
        msg = reshuffle_existing_questions()
        flash(msg, 'success')
    except Exception as e:
        flash(f'خطأ أثناء إعادة الخلط: {e}', 'danger')
    return redirect(url_for('pro_license.admin_index'))

# ─────────────────────────────────────────────
# أسئلة مزودة برسومات — لوحة المشرف
# ─────────────────────────────────────────────
@pro_license_bp.route('/admin/pro-license/drawings')
@login_required
@admin_required
def admin_drawings():
    std = request.args.get('standard', type=int)
    q_filter = ProLicenseQuestion.query.filter_by(has_drawing=True)
    if std:
        q_filter = q_filter.filter_by(standard_num=std)
    questions = q_filter.order_by(
        ProLicenseQuestion.standard_num,
        ProLicenseQuestion.id
    ).all()
    counts = {}
    for s in range(1, 19):
        counts[s] = ProLicenseQuestion.query.filter_by(has_drawing=True, standard_num=s).count()
    total = ProLicenseQuestion.query.filter_by(has_drawing=True).count()
    with_img = ProLicenseQuestion.query.filter(
        ProLicenseQuestion.has_drawing == True,
        ProLicenseQuestion.image_data != '',
        ProLicenseQuestion.image_data != None
    ).count()
    return render_template('admin_pro_drawings.html',
        questions=questions,
        selected_standard=std,
        pro_standards=PRO_STANDARDS,
        counts=counts,
        total=total,
        with_img=with_img,
    )


@pro_license_bp.route('/admin/pro-license/drawings/seed', methods=['POST'])
@login_required
@admin_required
def admin_drawings_seed():
    try:
        from data.pro_drawings_seed import DRAWING_QUESTIONS
        added = 0
        skipped = 0
        for q in DRAWING_QUESTIONS:
            exists = ProLicenseQuestion.query.filter_by(
                text=q['text'], standard_num=q['standard_num']
            ).first()
            if exists:
                skipped += 1
                continue
            std_info = PRO_STANDARDS.get(q['standard_num'], {})
            new_q = ProLicenseQuestion(
                text         = q['text'],
                option_a     = q['option_a'],
                option_b     = q['option_b'],
                option_c     = q['option_c'],
                option_d     = q['option_d'],
                answer       = q['answer'],
                explanation  = q.get('explanation', ''),
                standard_num = q['standard_num'],
                standard_name= std_info.get('name', ''),
                q_type       = std_info.get('type', 'educational'),
                difficulty   = q.get('difficulty', 'medium'),
                has_drawing  = True,
                is_active    = True,
                image_data   = '',
                created_by   = current_user.id,
            )
            db.session.add(new_q)
            added += 1
        db.session.commit()
        flash(f'✅ تم إضافة {added} سؤال مزود برسم ({skipped} موجود مسبقاً)', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ: {e}', 'danger')
    return redirect(url_for('pro_license.admin_drawings'))


@pro_license_bp.route('/admin/pro-license/drawings/upload-image/<int:qid>', methods=['POST'])
@login_required
@admin_required
def admin_drawings_upload_image(qid):
    import base64, os
    from werkzeug.utils import secure_filename
    q = ProLicenseQuestion.query.get_or_404(qid)
    if 'image' not in request.files:
        flash('لم يتم اختيار ملف', 'danger')
        return redirect(url_for('pro_license.admin_drawings', standard=q.standard_num))
    file = request.files['image']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'danger')
        return redirect(url_for('pro_license.admin_drawings', standard=q.standard_num))
    ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED:
        flash('نوع الملف غير مدعوم', 'danger')
        return redirect(url_for('pro_license.admin_drawings', standard=q.standard_num))
    # حفظ الصورة كـ base64 في قاعدة البيانات
    img_bytes = file.read()
    if len(img_bytes) > 5 * 1024 * 1024:
        flash('حجم الصورة أكبر من 5MB', 'danger')
        return redirect(url_for('pro_license.admin_drawings', standard=q.standard_num))
    mime = f'image/{ext}' if ext != 'jpg' else 'image/jpeg'
    encoded = base64.b64encode(img_bytes).decode('utf-8')
    q.image_data = f'data:{mime};base64,{encoded}'
    db.session.commit()
    flash(f'✅ تم رفع صورة السؤال #{qid}', 'success')
    return redirect(url_for('pro_license.admin_drawings', standard=q.standard_num))


@pro_license_bp.route('/admin/pro-license/drawings/remove-image/<int:qid>', methods=['POST'])
@login_required
@admin_required
def admin_drawings_remove_image(qid):
    q = ProLicenseQuestion.query.get_or_404(qid)
    q.image_data = ''
    db.session.commit()
    flash(f'تم حذف صورة السؤال #{qid}', 'info')
    return redirect(url_for('pro_license.admin_drawings', standard=q.standard_num))


# ─────────────────────────────────────────────
# صفحة الطالب الرئيسية
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license')
@login_required
def student_index():
    stats = {}
    for s_num, s_info in PRO_STANDARDS.items():
        cnt  = ProLicenseQuestion.query.filter_by(standard_num=s_num, is_active=True).count()
        last = ProLicenseResult.query.filter_by(
            user_id=current_user.id, standard_num=s_num
        ).order_by(ProLicenseResult.created_at.desc()).first()
        stats[s_num] = {
            'name': s_info['name'], 'type': s_info['type'],
            'count': cnt, 'last_result': last
        }

    today = date.today()
    today_session = DailyTrainingSession.query.filter_by(
        user_id=current_user.id, exam_date=today
    ).first()

    last_session = DailyTrainingSession.query.filter_by(
        user_id=current_user.id
    ).order_by(DailyTrainingSession.created_at.desc()).first()

    if today_session:
        day_num      = today_session.day_num
        review_count = 0
    elif last_session:
        day_num      = last_session.day_num + 1
        review_count = len(json.loads(last_session.wrong_ids or '[]'))
    else:
        day_num      = 1
        review_count = 0

    total_q = ProLicenseQuestion.query.filter_by(is_active=True).count()
    n_models = max(1, min(10, total_q // 36)) if total_q >= 36 else 0

    return render_template('student_pro_exam.html',
        standards   = PRO_STANDARDS,
        stats       = stats,
        today_done  = today_session is not None and today_session.completed,
        day_num     = day_num,
        review_count= review_count,
        n_models    = n_models,
        daily_score = today_session.score_pct if today_session and today_session.completed else None,
        total_q     = total_q,
    )

# ─────────────────────────────────────────────
# التدريب اليومي — بدء
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/daily/start')
@login_required
def daily_start():
    today = date.today()
    today_session = DailyTrainingSession.query.filter_by(
        user_id=current_user.id, exam_date=today
    ).first()
    if today_session and today_session.completed:
        flash('لقد أكملت تدريب اليوم بالفعل! عد غداً للتدريب التالي 🌟', 'info')
        return redirect(url_for('pro_license.student_index'))

    # إعادة استخدام جلسة اليوم غير المكتملة
    if today_session:
        all_ids = json.loads(today_session.review_ids or '[]') + json.loads(today_session.questions_ids or '[]')
        questions = ProLicenseQuestion.query.filter(
            ProLicenseQuestion.id.in_(all_ids), ProLicenseQuestion.is_active == True
        ).all()
        q_map = {q.id: q for q in questions}
        ordered = [q_map[i] for i in all_ids if i in q_map]
        review_count = len(json.loads(today_session.review_ids or '[]'))
        timer_seconds = request.args.get('timer', 0, type=int)
        return render_template('pro_exam_take.html',
            questions=ordered, standard=None,
            std_info={'name': f'التدريب اليومي — اليوم {today_session.day_num}', 'type': 'daily'},
            exam_type='daily', session_id=today_session.id,
            review_count=review_count, timer_seconds=timer_seconds,
        )

    last_session = DailyTrainingSession.query.filter_by(
        user_id=current_user.id
    ).order_by(DailyTrainingSession.created_at.desc()).first()

    day_num = (last_session.day_num + 1) if last_session else 1

    # أسئلة المراجعة (الأخطاء السابقة)
    review_questions = []
    if last_session:
        wrong_ids = json.loads(last_session.wrong_ids or '[]')
        if wrong_ids:
            rq = ProLicenseQuestion.query.filter(
                ProLicenseQuestion.id.in_(wrong_ids),
                ProLicenseQuestion.is_active == True
            ).all()
            review_questions = rq[:5]  # max 5 أسئلة مراجعة

    # تحديد الصعوبة تصاعدياً
    if day_num <= 3:
        diff_weights = [('easy', 0.6), ('medium', 0.4)]
    elif day_num <= 7:
        diff_weights = [('medium', 0.5), ('hard', 0.5)]
    else:
        diff_weights = [('hard', 0.65), ('medium', 0.35)]

    new_questions = []
    n_new = 15
    for diff, w in diff_weights:
        count = max(1, round(n_new * w))
        qs = ProLicenseQuestion.query.filter_by(
            difficulty=diff, is_active=True
        ).order_by(db.func.random()).limit(count).all()
        new_questions.extend(qs)

    random.shuffle(new_questions)
    new_questions = new_questions[:n_new]

    session_obj = DailyTrainingSession(
        user_id       = current_user.id,
        day_num       = day_num,
        exam_date     = today,
        questions_ids = json.dumps([q.id for q in new_questions]),
        review_ids    = json.dumps([q.id for q in review_questions]),
        wrong_ids     = '[]',
        completed     = False,
    )
    db.session.add(session_obj)
    db.session.commit()

    all_questions = review_questions + new_questions
    timer_seconds = request.args.get('timer', 0, type=int)

    return render_template('pro_exam_take.html',
        questions     = all_questions,
        standard      = None,
        std_info      = {'name': f'التدريب اليومي — اليوم {day_num}', 'type': 'daily'},
        exam_type     = 'daily',
        session_id    = session_obj.id,
        review_count  = len(review_questions),
        timer_seconds = timer_seconds,
    )

# ─────────────────────────────────────────────
# التدريب اليومي — تسليم
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/daily/submit/<int:session_id>', methods=['POST'])
@login_required
def submit_daily(session_id):
    session_obj = DailyTrainingSession.query.get_or_404(session_id)
    if session_obj.user_id != current_user.id:
        abort(403)

    all_ids   = json.loads(session_obj.review_ids or '[]') + json.loads(session_obj.questions_ids or '[]')
    questions = ProLicenseQuestion.query.filter(ProLicenseQuestion.id.in_(all_ids)).all()
    q_map     = {q.id: q for q in questions}

    user_answers  = {}
    score         = 0
    wrong_ids     = []
    submitted_ids = []

    for key, val in request.form.items():
        if key.startswith('q_'):
            qid = int(key[2:])
            ua  = val.upper()
            user_answers[str(qid)] = ua
            submitted_ids.append(qid)
            q = q_map.get(qid)
            if q:
                if q.answer == ua:
                    score += 1
                else:
                    wrong_ids.append(qid)

    if not submitted_ids:
        flash('لم تُجب على أي سؤال! حاول الإجابة على الأسئلة قبل التسليم.', 'warning')
        return redirect(url_for('pro_license.daily_start'))

    session_obj.wrong_ids = json.dumps(wrong_ids)
    session_obj.score     = score
    session_obj.total     = len(submitted_ids)
    session_obj.completed = True
    db.session.commit()

    result = ProLicenseResult(
        user_id      = current_user.id,
        standard_num = None,
        questions_ids= json.dumps(submitted_ids),
        user_answers = json.dumps(user_answers),
        score        = score,
        total        = len(submitted_ids),
        exam_type    = 'daily',
    )
    db.session.add(result)
    db.session.commit()
    return redirect(url_for('pro_license.exam_results', result_id=result.id))

# ─────────────────────────────────────────────
# نموذج اختبار
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/model-exam/<int:model_num>')
@login_required
def model_exam(model_num):
    questions = []
    for std_num in range(1, 19):
        std_qs = ProLicenseQuestion.query.filter_by(
            standard_num=std_num, is_active=True
        ).order_by(ProLicenseQuestion.id).all()
        if not std_qs:
            continue
        n = len(std_qs)
        if n == 1:
            questions.append(std_qs[0])
        else:
            idx1 = ((model_num - 1) * 2) % n
            idx2 = ((model_num - 1) * 2 + 1) % n
            questions.append(std_qs[idx1])
            if idx2 != idx1:
                questions.append(std_qs[idx2])

    if not questions:
        flash('لا توجد أسئلة بعد', 'warning')
        return redirect(url_for('pro_license.student_index'))

    random.shuffle(questions)
    timer_seconds = request.args.get('timer', 0, type=int)

    return render_template('pro_exam_take.html',
        questions     = questions,
        standard      = None,
        std_info      = {'name': f'نموذج اختبار رقم {model_num}', 'type': 'model'},
        exam_type     = 'model',
        model_num     = model_num,
        review_count  = 0,
        timer_seconds = timer_seconds,
    )

# ─────────────────────────────────────────────
# تسليم نموذج اختبار
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/model-exam/<int:model_num>/submit', methods=['POST'])
@login_required
def submit_model(model_num):
    user_answers  = {}
    score         = 0
    submitted_ids = []

    for key, val in request.form.items():
        if key.startswith('q_'):
            qid = int(key[2:])
            ua  = val.upper()
            user_answers[str(qid)] = ua
            submitted_ids.append(qid)

    if not submitted_ids:
        flash('لم تُجب على أي سؤال! حاول الإجابة على الأسئلة قبل التسليم.', 'warning')
        return redirect(url_for('pro_license.model_exam', model_num=model_num))

    questions = ProLicenseQuestion.query.filter(
        ProLicenseQuestion.id.in_(submitted_ids)
    ).all()
    q_map = {q.id: q for q in questions}
    for qid in submitted_ids:
        q = q_map.get(qid)
        if q and q.answer == user_answers.get(str(qid)):
            score += 1

    result = ProLicenseResult(
        user_id      = current_user.id,
        standard_num = None,
        questions_ids= json.dumps(submitted_ids),
        user_answers = json.dumps(user_answers),
        score        = score,
        total        = len(submitted_ids),
        exam_type    = f'model_{model_num}',
    )
    db.session.add(result)
    db.session.commit()
    return redirect(url_for('pro_license.exam_results', result_id=result.id))

# ─────────────────────────────────────────────
# اختبار شامل (كل المعايير)
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/comprehensive')
@login_required
def comprehensive_exam():
    questions = []
    for std_num in range(1, 19):
        qs = ProLicenseQuestion.query.filter_by(
            standard_num=std_num, is_active=True
        ).order_by(db.func.random()).limit(2).all()
        questions.extend(qs)

    if len(questions) < 5:
        flash('لا توجد أسئلة كافية بعد', 'warning')
        return redirect(url_for('pro_license.student_index'))

    random.shuffle(questions)
    timer_seconds = request.args.get('timer', 0, type=int)

    return render_template('pro_exam_take.html',
        questions     = questions,
        standard      = None,
        std_info      = {'name': 'الاختبار التجميعي الشامل (كل المعايير)', 'type': 'comprehensive'},
        exam_type     = 'comprehensive',
        review_count  = 0,
        timer_seconds = timer_seconds,
    )

# ─────────────────────────────────────────────
# تسليم الاختبار الشامل
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/comprehensive/submit', methods=['POST'])
@login_required
def submit_comprehensive():
    user_answers  = {}
    submitted_ids = []
    score         = 0

    for key, val in request.form.items():
        if key.startswith('q_'):
            qid = int(key[2:])
            ua  = val.upper()
            user_answers[str(qid)] = ua
            submitted_ids.append(qid)

    if not submitted_ids:
        flash('لم تُجب على أي سؤال! حاول الإجابة على الأسئلة قبل التسليم.', 'warning')
        return redirect(url_for('pro_license.comprehensive_exam'))

    questions = ProLicenseQuestion.query.filter(
        ProLicenseQuestion.id.in_(submitted_ids)
    ).all()
    q_map = {q.id: q for q in questions}
    for qid in submitted_ids:
        q = q_map.get(qid)
        if q and q.answer == user_answers.get(str(qid)):
            score += 1

    result = ProLicenseResult(
        user_id      = current_user.id,
        standard_num = None,
        questions_ids= json.dumps(submitted_ids),
        user_answers = json.dumps(user_answers),
        score        = score,
        total        = len(submitted_ids),
        exam_type    = 'comprehensive',
    )
    db.session.add(result)
    db.session.commit()
    return redirect(url_for('pro_license.exam_results', result_id=result.id))

# ─────────────────────────────────────────────
# بدء اختبار معيار
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/exam/<int:standard>')
@login_required
def start_exam(standard):
    questions = ProLicenseQuestion.query.filter_by(
        standard_num=standard, is_active=True
    ).order_by(db.func.random()).limit(20).all()

    if not questions:
        flash('لا توجد أسئلة لهذا المعيار بعد', 'warning')
        return redirect(url_for('pro_license.student_index'))

    std_info      = PRO_STANDARDS.get(standard, {})
    timer_seconds = request.args.get('timer', 0, type=int)

    return render_template('pro_exam_take.html',
        questions     = questions,
        standard      = standard,
        std_info      = std_info,
        exam_type     = 'standard',
        review_count  = 0,
        timer_seconds = timer_seconds,
    )

# ─────────────────────────────────────────────
# تسليم اختبار المعيار
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/submit/<int:standard>', methods=['POST'])
@login_required
def submit_exam(standard):
    user_answers  = {}
    score         = 0
    submitted_ids = []

    for key, val in request.form.items():
        if key.startswith('q_'):
            qid = int(key[2:])
            ua  = val.upper()
            user_answers[str(qid)] = ua
            submitted_ids.append(qid)

    if not submitted_ids:
        flash('لم تُجب على أي سؤال! حاول الإجابة على الأسئلة قبل التسليم.', 'warning')
        return redirect(url_for('pro_license.start_exam', standard=standard))

    questions = ProLicenseQuestion.query.filter(
        ProLicenseQuestion.id.in_(submitted_ids)
    ).all()
    q_map = {q.id: q for q in questions}
    for qid in submitted_ids:
        q = q_map.get(qid)
        if q and q.answer == user_answers.get(str(qid)):
            score += 1

    result = ProLicenseResult(
        user_id      = current_user.id,
        standard_num = standard,
        questions_ids= json.dumps(submitted_ids),
        user_answers = json.dumps(user_answers),
        score        = score,
        total        = len(submitted_ids),
        exam_type    = 'standard',
    )
    db.session.add(result)
    db.session.commit()
    return redirect(url_for('pro_license.exam_results', result_id=result.id))

# ─────────────────────────────────────────────
# نتائج الاختبار
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/results/<int:result_id>')
@login_required
def exam_results(result_id):
    result = ProLicenseResult.query.get_or_404(result_id)
    if result.user_id != current_user.id and not current_user.is_admin:
        flash('غير مسموح', 'danger')
        return redirect(url_for('pro_license.student_index'))

    ids       = json.loads(result.questions_ids)
    answers   = json.loads(result.user_answers)
    questions = ProLicenseQuestion.query.filter(ProLicenseQuestion.id.in_(ids)).all()
    q_map     = {q.id: q for q in questions}

    details        = []
    weak_standards = set()
    for qid_str, user_ans in answers.items():
        q = q_map.get(int(qid_str))
        if not q:
            continue
        correct = (user_ans == q.answer)
        if not correct:
            weak_standards.add(q.standard_num)
        details.append({'question': q, 'user_ans': user_ans, 'correct': correct})

    weak_info = {s: PRO_STANDARDS[s] for s in weak_standards if s in PRO_STANDARDS}
    std_info  = PRO_STANDARDS.get(result.standard_num, {})

    return render_template('pro_exam_results.html',
        result=result, details=details,
        weak_info=weak_info, std_info=std_info,
    )

# ─────────────────────────────────────────────
# سجل نتائج الطالب
# ─────────────────────────────────────────────
@pro_license_bp.route('/student/pro-license/history')
@login_required
def history():
    results = ProLicenseResult.query.filter_by(
        user_id=current_user.id
    ).order_by(ProLicenseResult.created_at.desc()).limit(50).all()
    return render_template('pro_exam_history.html',
        results=results, standards=PRO_STANDARDS)

# ═══════════════════════════════════════════════════
# استيراد دفعي للرخصة المهنية عبر الكود
# ═══════════════════════════════════════════════════
def _parse_pro_code(code: str) -> list:
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
    try:
        idx = code.index('[')
        end_idx = code.rindex(']') + 1
        result = ast.literal_eval(code[idx:end_idx])
        return result if isinstance(result, list) else []
    except Exception:
        return []

@pro_license_bp.route('/admin/pro-license/import', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_import():
    if request.method == 'GET':
        return render_template('admin_import_pro_questions.html',
                               standards=PRO_STANDARDS)

    data         = request.get_json()
    code         = data.get('code', '').strip()
    standard_num = int(data.get('standard_num', 1))
    diff         = data.get('difficulty', '')

    questions = _parse_pro_code(code)
    if not questions:
        return jsonify({'success': False, 'error': 'لم يتم التعرف على أي أسئلة في الكود'})

    required = {'text', 'option_a', 'option_b', 'option_c', 'option_d', 'answer'}
    added = 0
    skipped = 0
    for q in questions:
        if not required.issubset(q.keys()):
            skipped += 1
            continue
        existing = ProLicenseQuestion.query.filter_by(
            text=q.get('text', ''), standard_num=standard_num).first()
        if existing:
            skipped += 1
            continue
        pq = ProLicenseQuestion(
            standard_num = standard_num,
            text         = q['text'],
            option_a     = q['option_a'],
            option_b     = q['option_b'],
            option_c     = q['option_c'],
            option_d     = q['option_d'],
            answer       = q['answer'].upper(),
            explanation  = q.get('explanation', ''),
            difficulty   = q.get('difficulty', diff or 'medium'),
        )
        db.session.add(pq)
        added += 1
    db.session.commit()
    return jsonify({'success': True, 'added': added,
                    'total': len(questions), 'skipped': skipped})

@pro_license_bp.route('/admin/pro-license/ai-fix-code', methods=['POST'])
@login_required
@admin_required
def admin_ai_fix_code():
    from services.ai_service import fix_import_code
    data = request.get_json()
    code = data.get('code', '')
    if not code.strip():
        return jsonify({'success': False, 'error': 'الكود فارغ'})
    result = fix_import_code(code)
    return jsonify({'success': True, **result})

@pro_license_bp.route('/admin/pro-license/preview-code', methods=['POST'])
@login_required
@admin_required
def admin_preview_code():
    data = request.get_json()
    code = data.get('code', '')
    questions = _parse_pro_code(code)
    required  = {'text', 'option_a', 'option_b', 'option_c', 'option_d', 'answer'}
    valid     = [q for q in questions if required.issubset(q.keys())]
    invalid   = len(questions) - len(valid)
    preview   = [{'text': q.get('text','')[:80], 'answer': q.get('answer','')} for q in valid[:5]]
    return jsonify({'success': True, 'total': len(questions),
                    'valid': len(valid), 'invalid': invalid, 'preview': preview})
