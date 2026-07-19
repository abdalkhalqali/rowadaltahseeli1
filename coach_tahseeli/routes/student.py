from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session as flask_session
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import json, random
from extensions import db
from models import User, Question, Evaluation
from models.daily_training import DailyTraining
from services.assessment_service import run_assessment, save_assessment_results
from services.question_service import (get_exam_questions, get_daily_questions,
                                       get_comprehensive_questions, get_weekly_questions,
                                       get_smart_daily_questions, GRADE_MAP)

student_bp = Blueprint('student', __name__)

SUBJECTS = {
    'physics':   {'ar': 'الفيزياء',    'icon': '⚛️',  'color': '#00E5FF'},
    'chemistry': {'ar': 'الكيمياء',    'icon': '🧪',  'color': '#FFB800'},
    'biology':   {'ar': 'الأحياء',     'icon': '🧬',  'color': '#10B981'},
    'math':      {'ar': 'الرياضيات',   'icon': '📐',  'color': '#7C3AED'},
}

EXAM_TYPES = {
    'level_test':      'تقييم المستوى',
    'daily_train':     'تدريب يومي',
    'quick_test':      'اختبار سريع',
    'chapter_1':       'الفصل الأول',
    'chapter_2':       'الفصل الثاني',
    'final_test':      'اختبار شامل',
    'past_model':      'نموذج تحصيلي',
    'past_1446':       'نموذج تحصيلي 1446 هـ',
    'past_1445':       'نموذج تحصيلي 1445 هـ',
    'past_1444':       'نموذج تحصيلي 1444 هـ',
    'past_1443':       'نموذج تحصيلي 1443 هـ',
    'expected_model':  'اختبار متوقع 1447 هـ',
}

# ── عدد الأسئلة المتاحة لكل نوع ──
LEVEL_COUNTS  = [10, 20, 30, 50, 100]
DAILY_COUNTS  = [5, 10, 15, 20, 30]

@student_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    recent = (Evaluation.query
              .filter_by(user_id=current_user.id)
              .order_by(Evaluation.created_at.desc())
              .limit(5).all())
    stats = {s: _subject_stats(s) for s in SUBJECTS}
    weak  = current_user.get_weak_points_list()
    daily_info = {s: _daily_info(s) for s in SUBJECTS}
    pro_analysis = _quick_pro_analysis(stats)
    return render_template('student_dashboard.html',
                           subjects=SUBJECTS, exam_types=EXAM_TYPES,
                           recent=recent, stats=stats, weak=weak,
                           daily_info=daily_info,
                           level_counts=LEVEL_COUNTS,
                           daily_counts=DAILY_COUNTS,
                           pro_analysis=pro_analysis)

SUBJECT_AR = {
    'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
    'biology': 'الأحياء',  'math': 'الرياضيات',
}

def _quick_pro_analysis(stats: dict) -> dict:
    """تحليل خفيف للداشبورد — يعتمد على متوسط الدرجات"""
    weak, medium, strong = [], [], []
    for subj, s in stats.items():
        if s['count'] == 0:
            medium.append(subj)
        elif s['avg'] < 50:
            weak.append(subj)
        elif s['avg'] < 72:
            medium.append(subj)
        else:
            strong.append(subj)
    has_history = any(s['count'] > 0 for s in stats.values())
    return {
        'weak': weak, 'medium': medium, 'strong': strong,
        'has_history': has_history,
        'avgs': {s: stats[s]['avg'] for s in stats},
    }

def _subject_stats(subject):
    evals = Evaluation.query.filter_by(user_id=current_user.id, subject=subject).all()
    if not evals:
        return {'count': 0, 'avg': 0, 'best': 0}
    scores = [e.score_pct for e in evals]
    return {'count': len(evals), 'avg': round(sum(scores)/len(scores), 1), 'best': max(scores)}

def _daily_info(subject):
    last   = DailyTraining.get_last_session(current_user.id, subject)
    day_no = DailyTraining.get_next_day_number(current_user.id, subject)
    absent = DailyTraining.count_absences(current_user.id, subject)
    repeated = 0
    if last and last.completed:
        yesterday = date.today() - timedelta(days=1)
        if last.training_date == yesterday:
            repeated = len(last.get_wrong_ids())
    return {
        'day_number': day_no,
        'absences':   absent,
        'repeated':   repeated,
    }

# ── اختبار تقييم المستوى (مع تحديد عدد الأسئلة) ──
@student_bp.route('/exam/<subject>/<exam_type>', methods=['GET', 'POST'])
@login_required
def exam(subject, exam_type):
    if subject not in SUBJECTS:
        flash('مادة غير صحيحة', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        data       = request.get_json()
        answers    = data.get('answers', {})
        q_ids      = data.get('question_ids', [])
        time_taken = data.get('time_taken', 0)

        questions = Question.query.filter(Question.id.in_(q_ids)).all()
        correct = sum(1 for q in questions if answers.get(str(q.id), '').upper() == q.answer.upper())
        pct     = round((correct / len(questions)) * 100, 1) if questions else 0

        ev = Evaluation(
            user_id=current_user.id, eval_type='exam',
            subject=subject, exam_type=exam_type,
            grade=current_user.grade,
            total_q=len(questions), correct=correct, score_pct=pct,
            time_taken=time_taken
        )
        ev.set_questions_ids(q_ids)
        ev.set_user_answers(answers)
        db.session.add(ev)
        current_user.total_score += correct
        current_user.exams_taken += 1
        db.session.commit()

        # إشعار المشرفين بنتيجة الاختبار
        try:
            from routes.notifications import notify_admins
            _SUBJ_AR = {'physics':'الفيزياء','chemistry':'الكيمياء','biology':'الأحياء','math':'الرياضيات'}
            _TYPE_AR = {'level_test':'اختبار تقييم المستوى','daily_train':'تدريب يومي',
                        'chapter_test':'اختبار فصل','weekly_challenge':'تحدي أسبوعي'}
            notify_admins(
                title=f'📊 {current_user.name} أجرى اختباراً — {pct}%',
                body=(f'الطالب «{current_user.name}»\n'
                      f'النوع: {_TYPE_AR.get(exam_type, exam_type)} — المادة: {_SUBJ_AR.get(subject, subject)}\n'
                      f'النتيجة: {pct}% ({correct} من {len(questions)} إجابة صحيحة)'),
                link=f'/admin/users/{current_user.id}',
                filter_key='exam',
            )
        except Exception:
            pass

        return jsonify({'redirect': url_for('student.results', eval_id=ev.id)})

    # GET — عدد الأسئلة مخصص لـ level_test
    custom_limit = None
    if exam_type == 'level_test':
        try:
            custom_limit = int(request.args.get('count', 20))
            custom_limit = min(max(custom_limit, 10), 100)
        except (ValueError, TypeError):
            custom_limit = 20

    # السماح بتمرير الصف من التبويب (يُقدَّم على صف المستخدم المحفوظ)
    grade_filter = request.args.get('grade_filter', current_user.grade)
    valid_grades = ('grade_10', 'grade_11', 'grade_12', 'all_grades', 'unknown')
    if grade_filter not in valid_grades:
        grade_filter = current_user.grade

    difficulty_filter = request.args.get('difficulty', '')
    if difficulty_filter not in ('easy', 'medium', 'hard', ''):
        difficulty_filter = ''

    questions = get_exam_questions(subject, exam_type, grade_filter,
                                   custom_limit=custom_limit,
                                   difficulty=difficulty_filter or None)
    if not questions:
        flash('لا تتوفر أسئلة لهذا الاختبار حتى الآن', 'warning')
        return redirect(url_for('student.dashboard'))

    random.shuffle(questions)
    return render_template('exam.html',
                           questions=questions, subject=subject,
                           exam_type=exam_type,
                           subject_info=SUBJECTS[subject],
                           exam_type_ar=EXAM_TYPES.get(exam_type, exam_type),
                           duration=_get_duration(exam_type))

# ── التدريب اليومي (مع تتبع التقدم والصعوبة التدريجية) ──
@student_bp.route('/daily-train/<subject>', methods=['GET', 'POST'])
@login_required
def daily_train(subject):
    if subject not in SUBJECTS:
        flash('مادة غير صحيحة', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        data       = request.get_json()
        answers    = data.get('answers', {})
        q_ids      = data.get('question_ids', [])
        time_taken = data.get('time_taken', 0)

        questions = Question.query.filter(Question.id.in_(q_ids)).all()
        correct   = sum(1 for q in questions if answers.get(str(q.id), '').upper() == q.answer.upper())
        pct       = round((correct / len(questions)) * 100, 1) if questions else 0
        wrong_ids = [q.id for q in questions if answers.get(str(q.id), '').upper() != q.answer.upper()]

        # تحديث سجل التدريب اليومي
        dt_id = flask_session.get(f'daily_session_{subject}')
        if dt_id:
            dt = DailyTraining.query.get(dt_id)
            if dt and dt.user_id == current_user.id:
                dt.correct   = correct
                dt.score_pct = pct
                dt.completed = True
                dt.set_wrong_ids(wrong_ids)

        ev = Evaluation(
            user_id=current_user.id, eval_type='daily_train',
            subject=subject, exam_type='daily_train',
            grade=current_user.grade,
            total_q=len(questions), correct=correct, score_pct=pct,
            time_taken=time_taken
        )
        ev.set_questions_ids(q_ids)
        ev.set_user_answers(answers)
        db.session.add(ev)
        current_user.total_score += correct
        current_user.exams_taken += 1
        db.session.commit()

        # إشعار المشرفين بنتيجة التدريب اليومي
        try:
            from routes.notifications import notify_admins
            _SUBJ_AR = {'physics':'الفيزياء','chemistry':'الكيمياء','biology':'الأحياء','math':'الرياضيات'}
            notify_admins(
                title=f'🏋️ {current_user.name} أتم تدريباً يومياً — {pct}%',
                body=(f'الطالب «{current_user.name}»\n'
                      f'المادة: {_SUBJ_AR.get(subject, subject)}\n'
                      f'النتيجة: {pct}% ({correct} من {len(questions)} إجابة صحيحة)'),
                link=f'/admin/users/{current_user.id}',
                filter_key='exam',
            )
        except Exception:
            pass

        flask_session.pop(f'daily_session_{subject}', None)
        return jsonify({'redirect': url_for('student.results', eval_id=ev.id)})

    # GET — بناء جلسة التدريب اليومي
    try:
        count = int(request.args.get('count', 15))
        count = min(max(count, 5), 30)
    except (ValueError, TypeError):
        count = 15

    # السماح بتمرير الصف من التبويب
    grade_filter = request.args.get('grade_filter', current_user.grade)
    valid_grades = ('grade_10', 'grade_11', 'grade_12', 'all_grades', 'unknown')
    if grade_filter not in valid_grades:
        grade_filter = current_user.grade

    grade    = grade_filter
    user_id  = current_user.id
    today    = date.today()

    last       = DailyTraining.get_last_session(user_id, subject)
    day_number = DailyTraining.get_next_day_number(user_id, subject)

    # أسئلة مكررة من الأمس (التي أخطأ فيها)
    repeated_ids      = []
    wrong_questions_d = []
    if last and last.completed:
        yesterday = today - timedelta(days=1)
        if last.training_date == yesterday:
            repeated_ids = last.get_wrong_ids()
            if repeated_ids:
                wrong_qs         = Question.query.filter(Question.id.in_(repeated_ids)).all()
                wrong_questions_d = [_q_to_dict_simple(q) for q in wrong_qs]

    # أسئلة جديدة بصعوبة تدريجية
    new_count     = max(0, count - len(wrong_questions_d))
    new_questions = get_daily_questions(subject, grade, day_number, new_count, exclude_ids=repeated_ids)

    all_questions = wrong_questions_d + new_questions
    random.shuffle(all_questions)
    all_questions = all_questions[:count]

    if not all_questions:
        flash('لا تتوفر أسئلة للتدريب اليومي حتى الآن', 'warning')
        return redirect(url_for('student.dashboard'))

    # إنشاء سجل التدريب
    dt = DailyTraining(
        user_id=user_id,
        subject=subject,
        grade=GRADE_MAP.get(grade, ''),
        training_date=today,
        day_number=day_number,
        total_q=len(all_questions)
    )
    dt.set_questions_ids([q['id'] for q in all_questions])
    dt.set_repeated_ids(repeated_ids)
    db.session.add(dt)
    db.session.commit()

    flask_session[f'daily_session_{subject}'] = dt.id

    absences = DailyTraining.count_absences(user_id, subject)

    diff_label = {
        range(1, 6):   'مبتدئ',
        range(6, 11):  'متوسط',
        range(11, 16): 'متقدم',
    }
    level_ar = 'خبير'
    for rng, lbl in diff_label.items():
        if day_number in rng:
            level_ar = lbl
            break

    return render_template('exam.html',
                           questions=all_questions, subject=subject,
                           exam_type='daily_train',
                           subject_info=SUBJECTS[subject],
                           exam_type_ar=f'تدريب يومي — اليوم {day_number} ({level_ar})',
                           duration=_get_duration('daily_train'),
                           day_number=day_number,
                           absences=absences,
                           repeated_count=len(wrong_questions_d))

def _q_to_dict_simple(q):
    return {
        'id': q.id, 'text': q.text,
        'option_a': q.option_a, 'option_b': q.option_b,
        'option_c': q.option_c, 'option_d': q.option_d,
        'answer': q.answer, 'explanation': q.explanation or '',
        'subject': q.subject, 'difficulty': q.difficulty or '',
        'lesson': q.lesson or '', 'grade': q.grade or '',
        'chapter': q.chapter or '', 'exam_type': q.exam_type or '',
    }

def _get_duration(exam_type):
    durations = {'quick_test': 10, 'level_test': 20, 'daily_train': 20,
                 'chapter_1': 25, 'chapter_2': 25, 'final_test': 45,
                 'past_1446': 45, 'past_1445': 45, 'past_1444': 45, 'past_1443': 45,
                 'expected_model': 45}
    return durations.get(exam_type, 20)

GRADE_AR = {
    'grade_10': 'الصف الأول ثانوي',
    'grade_11': 'الصف الثاني ثانوي',
    'grade_12': 'الصف الثالث ثانوي',
}

@student_bp.route('/results/<int:eval_id>')
@login_required
def results(eval_id):
    ev = Evaluation.query.get_or_404(eval_id)
    if ev.user_id != current_user.id and not current_user.is_admin:
        flash('غير مصرح لك', 'danger')
        return redirect(url_for('student.dashboard'))

    q_ids     = ev.get_questions_ids()
    answers   = ev.get_user_answers()
    questions = Question.query.filter(Question.id.in_(q_ids)).all()
    q_map     = {str(q.id): q for q in questions}

    # ── تحليل مفصّل: مادة × صف ──────────────────────────
    VALID_GRADES = ('grade_10', 'grade_11', 'grade_12')
    breakdown = {}
    for subj in SUBJECTS:
        breakdown[subj] = {
            g: {'correct': 0, 'wrong': 0, 'wrong_qs': []}
            for g in VALID_GRADES
        }
        breakdown[subj]['total_correct'] = 0
        breakdown[subj]['total_wrong']   = 0

    for qid in q_ids:
        q = q_map.get(str(qid))
        if not q or q.subject not in SUBJECTS:
            continue
        g = q.grade if q.grade in VALID_GRADES else 'grade_12'
        user_ans   = answers.get(str(qid), '')
        is_correct = user_ans.upper() == q.answer.upper()
        if is_correct:
            breakdown[q.subject][g]['correct']       += 1
            breakdown[q.subject]['total_correct']    += 1
        else:
            breakdown[q.subject][g]['wrong']         += 1
            breakdown[q.subject][g]['wrong_qs'].append(q)
            breakdown[q.subject]['total_wrong']      += 1

    # احذف المواد التي لا توجد بها أسئلة
    breakdown = {s: d for s, d in breakdown.items()
                 if d['total_correct'] + d['total_wrong'] > 0}

    # أضف إحصائيات مدمجة لكل مادة
    for subj, d in breakdown.items():
        total      = d['total_correct'] + d['total_wrong']
        wrong_pct  = round(d['total_wrong'] / total * 100, 1) if total else 0
        d['total']      = total
        d['wrong_pct']  = wrong_pct
        d['correct_pct']= round(100 - wrong_pct, 1)
        d['severity']   = ('critical' if wrong_pct >= 60
                           else 'moderate' if wrong_pct >= 30
                           else 'good')

    # ── توصيات: مرتّبة تنازلياً حسب الأخطاء ──────────────
    recommendations = []
    for subj, d in sorted(breakdown.items(),
                          key=lambda x: x[1]['total_wrong'], reverse=True):
        if d['total_wrong'] == 0:
            continue
        grade_errors = [(g, d[g]['wrong']) for g in VALID_GRADES if d[g]['wrong'] > 0]
        grade_errors.sort(key=lambda x: x[1], reverse=True)
        for grade, cnt in grade_errors:
            recommendations.append({
                'subject':     subj,
                'grade':       grade,
                'wrong_count': cnt,
                'severity':    d['severity'],
                'train_url':   url_for('student.daily_train', subject=subj)
                               + f'?grade_filter={grade}&count=20',
            })

    # ── مقارنة بآخر محاولة (نفس المادة + نوع الاختبار) ───
    prev_ev = None
    if ev.subject in SUBJECTS:
        prev_ev = (Evaluation.query
                   .filter_by(user_id=current_user.id,
                              subject=ev.subject, exam_type=ev.exam_type)
                   .filter(Evaluation.id != ev.id)
                   .order_by(Evaluation.created_at.desc())
                   .first())

    # ── بيانات الرادار (نسبة الصح لكل مادة) ─────────────
    radar_data = {s: breakdown[s]['correct_pct'] if s in breakdown else 0
                  for s in SUBJECTS}

    # ترتيب المواد: الأكثر خطأً أولاً
    breakdown_sorted = sorted(breakdown.items(),
                              key=lambda x: x[1]['total_wrong'], reverse=True)

    return render_template('results.html',
                           ev=ev, q_map=q_map, answers=answers,
                           subjects=SUBJECTS, grade_ar=GRADE_AR,
                           breakdown=breakdown,
                           breakdown_sorted=breakdown_sorted,
                           recommendations=recommendations,
                           prev_ev=prev_ev,
                           radar_data=radar_data)

@student_bp.route('/assessment', methods=['GET', 'POST'])
@login_required
def assessment():
    if current_user.is_assessed:
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        data    = request.get_json()
        answers = data.get('answers', {})
        results = run_assessment(answers)
        save_assessment_results(current_user, results)
        return jsonify({'redirect': url_for('student.assessment_results')})

    # GET — إما شاشة اختيار العدد أو الاختبار الفعلي
    try:
        count = int(request.args.get('count', 0))
        count = min(max(count, 40), 100)
    except (ValueError, TypeError):
        count = 0

    if count == 0:
        return render_template('assessment.html', show_selector=True, questions=None)

    questions = _get_assessment_questions(count)
    return render_template('assessment.html', show_selector=False, questions=questions)

def _get_assessment_questions(count: int = 40):
    from data.level_assessment.physics_assessment   import PHYSICS_ASSESSMENT
    from data.level_assessment.chemistry_assessment import CHEMISTRY_ASSESSMENT
    from data.level_assessment.biology_assessment   import BIOLOGY_ASSESSMENT
    from data.level_assessment.math_assessment      import MATH_ASSESSMENT

    pools = {
        'physics':   PHYSICS_ASSESSMENT[:],
        'chemistry': CHEMISTRY_ASSESSMENT[:],
        'biology':   BIOLOGY_ASSESSMENT[:],
        'math':      MATH_ASSESSMENT[:],
    }
    for p in pools.values():
        random.shuffle(p)

    # أخذ 10 سؤال من كل مادة من ملفات البيانات
    base = []
    for qs in pools.values():
        base.extend(qs[:10])
    random.shuffle(base)

    # إذا طُلب أكثر من 40، نكمّل من قاعدة البيانات
    if count > 40:
        extra_needed = count - 40
        per_subj = extra_needed // 4
        rem = extra_needed % 4
        for i, subj in enumerate(SUBJECTS):
            n = per_subj + (1 if i < rem else 0)
            if n <= 0:
                continue
            db_qs = get_exam_questions(subj, 'level_test', 'all_grades', custom_limit=n)
            for dq in db_qs:
                # تحويل إلى نفس تنسيق أسئلة التقييم
                dq.setdefault('id', dq.get('id', str(random.randint(10000, 99999))))
                base.append(dq)
        random.shuffle(base)

    return base[:count]

@student_bp.route('/assessment-results')
@login_required
def assessment_results():
    if not current_user.is_assessed:
        return redirect(url_for('student.assessment'))
    weak = current_user.get_weak_points_list()
    return render_template('assessment_results.html', weak=weak,
                           level=current_user.level, subjects=SUBJECTS)

@student_bp.route('/set-grade', methods=['POST'])
@login_required
def set_grade():
    grade = request.form.get('grade', '')
    valid = ('grade_10', 'grade_11', 'grade_12', 'all_grades')
    if grade in valid:
        current_user.grade = grade
        db.session.commit()
    return redirect(url_for('student.dashboard'))

@student_bp.route('/skill-assessment')
@login_required
def skill_assessment():
    return render_template('skill_assessment.html', subjects=SUBJECTS)

@student_bp.route('/progress')
@login_required
def progress():
    evals = (Evaluation.query.filter_by(user_id=current_user.id)
             .order_by(Evaluation.created_at.desc()).all())
    return render_template('progress.html', evals=evals, subjects=SUBJECTS)


# ══════════════════════════════════════════════════
# § تدريبات المحترفين
# ══════════════════════════════════════════════════

@student_bp.route('/pro/comprehensive', methods=['GET', 'POST'])
@login_required
def pro_comprehensive():
    if request.method == 'POST':
        data       = request.get_json()
        answers    = data.get('answers', {})
        q_ids      = data.get('question_ids', [])
        time_taken = data.get('time_taken', 0)
        questions  = Question.query.filter(Question.id.in_(q_ids)).all()
        correct    = sum(1 for q in questions
                        if answers.get(str(q.id), '').upper() == q.answer.upper())
        pct        = round((correct / len(questions)) * 100, 1) if questions else 0
        ev = Evaluation(
            user_id=current_user.id, eval_type='exam',
            subject='comprehensive', exam_type='comprehensive',
            grade=current_user.grade,
            total_q=len(questions), correct=correct, score_pct=pct,
            time_taken=time_taken
        )
        ev.set_questions_ids(q_ids)
        ev.set_user_answers(answers)
        db.session.add(ev)
        current_user.total_score += correct
        current_user.exams_taken += 1
        db.session.commit()
        return jsonify({'redirect': url_for('student.results', eval_id=ev.id)})

    try:
        count = int(request.args.get('count', 40))
        count = min(max(count, 20), 80)
    except (ValueError, TypeError):
        count = 40

    questions = get_comprehensive_questions(count)
    if not questions:
        flash('لا تتوفر أسئلة كافية للاختبار الشامل', 'warning')
        return redirect(url_for('student.dashboard'))

    random.shuffle(questions)
    return render_template('exam.html',
                           questions=questions,
                           subject='comprehensive',
                           exam_type='comprehensive',
                           subject_info={'ar': 'شامل كل المواد', 'icon': '🌐', 'color': '#00E5FF'},
                           exam_type_ar='⚡ الاختبار الشامل',
                           duration=60)


@student_bp.route('/pro/weekly', methods=['GET', 'POST'])
@login_required
def pro_weekly():
    from datetime import datetime
    _, week_num, _ = datetime.now().isocalendar()

    if request.method == 'POST':
        data       = request.get_json()
        answers    = data.get('answers', {})
        q_ids      = data.get('question_ids', [])
        time_taken = data.get('time_taken', 0)
        questions  = Question.query.filter(Question.id.in_(q_ids)).all()
        correct    = sum(1 for q in questions
                        if answers.get(str(q.id), '').upper() == q.answer.upper())
        pct        = round((correct / len(questions)) * 100, 1) if questions else 0
        ev = Evaluation(
            user_id=current_user.id, eval_type='exam',
            subject='weekly', exam_type='weekly_challenge',
            grade=current_user.grade,
            total_q=len(questions), correct=correct, score_pct=pct,
            time_taken=time_taken
        )
        ev.set_questions_ids(q_ids)
        ev.set_user_answers(answers)
        db.session.add(ev)
        current_user.total_score += correct
        current_user.exams_taken += 1
        db.session.commit()
        return jsonify({'redirect': url_for('student.results', eval_id=ev.id)})

    questions = get_weekly_questions(40)
    if not questions:
        flash('لا تتوفر أسئلة لتحدي الأسبوع', 'warning')
        return redirect(url_for('student.dashboard'))

    return render_template('exam.html',
                           questions=questions,
                           subject='weekly',
                           exam_type='weekly_challenge',
                           subject_info={'ar': f'تحدي الأسبوع {week_num}', 'icon': '🔥', 'color': '#f43f5e'},
                           exam_type_ar=f'🔥 تحدي الأسبوع #{week_num}',
                           duration=50)


@student_bp.route('/pro/smart-daily', methods=['GET', 'POST'])
@login_required
def pro_smart_daily():
    if request.method == 'POST':
        data       = request.get_json()
        answers    = data.get('answers', {})
        q_ids      = data.get('question_ids', [])
        time_taken = data.get('time_taken', 0)
        questions  = Question.query.filter(Question.id.in_(q_ids)).all()
        correct    = sum(1 for q in questions
                        if answers.get(str(q.id), '').upper() == q.answer.upper())
        pct        = round((correct / len(questions)) * 100, 1) if questions else 0
        ev = Evaluation(
            user_id=current_user.id, eval_type='exam',
            subject='smart_daily', exam_type='smart_daily',
            grade=current_user.grade,
            total_q=len(questions), correct=correct, score_pct=pct,
            time_taken=time_taken
        )
        ev.set_questions_ids(q_ids)
        ev.set_user_answers(answers)
        db.session.add(ev)
        current_user.total_score += correct
        current_user.exams_taken += 1
        db.session.commit()
        return jsonify({'redirect': url_for('student.results', eval_id=ev.id)})

    try:
        count = int(request.args.get('count', 40))
        count = min(max(count, 40), 80)
    except (ValueError, TypeError):
        count = 40

    questions, analysis = get_smart_daily_questions(current_user.id, count)
    if not questions:
        flash('لا تتوفر أسئلة كافية للجلسة اليومية', 'warning')
        return redirect(url_for('student.dashboard'))

    subj_ar = {'physics':'الفيزياء','chemistry':'الكيمياء',
                'biology':'الأحياء','math':'الرياضيات'}
    focus = ' · '.join(subj_ar.get(s,'') for s in analysis.get('weak', [])[:2]) or 'متوازن'

    return render_template('exam.html',
                           questions=questions,
                           subject='smart_daily',
                           exam_type='smart_daily',
                           subject_info={'ar': 'جلسة البناء اليومية', 'icon': '🧠', 'color': '#8B5CF6'},
                           exam_type_ar=f'🧠 جلسة البناء — تركيز: {focus}',
                           duration=30)


# ── حذف الحساب ────────────────────────────────────────────────
@student_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    from flask_login import logout_user
    from models.evaluation import Evaluation
    from models.notification import Notification
    from models.community import CommunityPost
    from models.direct_message import DirectMessage
    from models.story import Story
    uid = current_user.id
    logout_user()
    Story.query.filter_by(user_id=uid).delete()
    Evaluation.query.filter_by(user_id=uid).delete()
    Notification.query.filter_by(user_id=uid).delete()
    DirectMessage.query.filter(
        (DirectMessage.sender_id == uid) | (DirectMessage.recipient_id == uid)
    ).delete()
    CommunityPost.query.filter_by(user_id=uid).delete()
    user = User.query.get(uid)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash('تم حذف حسابك بنجاح. نتمنى لك التوفيق 🎓', 'info')
    return redirect(url_for('index'))


# ── تحديث النبذة الشخصية ─────────────────────────────────────
@student_bp.route('/update-bio', methods=['POST'])
@login_required
def update_bio():
    bio = request.form.get('bio', '').strip()[:300]
    current_user.bio = bio
    db.session.commit()
    return jsonify({'success': True, 'bio': bio})
