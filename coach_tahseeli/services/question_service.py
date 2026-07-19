from models import Question
from extensions import db
import random

GRADE_MAP = {
    'grade_10': '1', 'grade_11': '2', 'grade_12': '3',
    '1': '1', '2': '2', '3': '3',
    'all_grades': None, '': None, None: None,
}

def _q_to_dict(q):
    return {
        'id': q.id,
        'text': q.text,
        'option_a': q.option_a,
        'option_b': q.option_b,
        'option_c': q.option_c,
        'option_d': q.option_d,
        'answer': q.answer,
        'explanation': q.explanation or '',
        'subject': q.subject,
        'difficulty': q.difficulty or '',
        'lesson': q.lesson or '',
        'grade': q.grade or '',
        'chapter': q.chapter or '',
        'exam_type': q.exam_type or '',
        'image_path': q.image_path or '',
        'code_snippet': q.code_snippet or '',
        'code_type': q.code_type or 'python',
    }

PAST_MODEL_TYPES = {'past_model', 'past_1446', 'past_1445', 'past_1444', 'past_1443'}

def get_exam_questions(subject: str, exam_type: str, grade: str,
                        custom_limit: int = None, difficulty: str = None) -> list:
    grade_db = GRADE_MAP.get(grade)

    # ── نماذج سابقة: تسحب من أسئلة التحصيلي بأسلوبه الحقيقي ──
    if exam_type in PAST_MODEL_TYPES:
        q = Question.query.filter_by(
            subject=subject, is_active=True, source='tahseel_style'
        )
        if difficulty:
            q = q.filter_by(difficulty=difficulty)
        questions = q.all()
        limit = custom_limit or 40
        if len(questions) > limit:
            questions = random.sample(questions, limit)
        return [_q_to_dict(q) for q in questions]

    # ── اختبارات متوقعة: تسحب من كل أسئلة التحصيلي للمادة ──
    if exam_type == 'expected_model':
        q = Question.query.filter_by(
            subject=subject, is_active=True, source='tahseel_style'
        )
        if difficulty:
            q = q.filter_by(difficulty=difficulty)
        questions = q.all()
        limit = custom_limit or 40
        if len(questions) > limit:
            questions = random.sample(questions, limit)
        return [_q_to_dict(q) for q in questions]

    fallback_chains = {
        'chapter_1':   [('chapter_1',)],
        'chapter_2':   [('chapter_2',)],
        'level_test':  [('level_test',)],
        'daily_train': [('daily_train',), ('level_test',)],
        'quick_test':  [('quick_test',),  ('level_test',)],
        'final_test':  [('final_test', 'chapter_1', 'chapter_2'), ('level_test',)],
    }

    default_limits = {
        'quick_test': 10, 'level_test': 20, 'daily_train': 15,
        'chapter_1': 20, 'chapter_2': 20, 'final_test': 40
    }
    limit = custom_limit if custom_limit else default_limits.get(exam_type, 20)

    chain = fallback_chains.get(exam_type, [None])
    questions = []

    for types in chain:
        q = Question.query.filter_by(subject=subject, is_active=True)
        if grade_db:
            q = q.filter_by(grade=grade_db)
        if difficulty:
            q = q.filter_by(difficulty=difficulty)
        if types:
            q = q.filter(Question.exam_type.in_(types))
        questions = q.all()
        if questions:
            break

    if not questions:
        q = Question.query.filter_by(subject=subject, is_active=True)
        if grade_db:
            q = q.filter_by(grade=grade_db)
        if difficulty:
            q = q.filter_by(difficulty=difficulty)
        questions = q.all()

    if not questions and difficulty:
        q = Question.query.filter_by(subject=subject, is_active=True)
        if grade_db:
            q = q.filter_by(grade=grade_db)
        questions = q.all()

    if len(questions) > limit:
        questions = random.sample(questions, limit)

    return [_q_to_dict(q) for q in questions]


def get_comprehensive_questions(count: int) -> list:
    subjects = ['physics', 'chemistry', 'biology', 'math']
    per_subject = max(count // 4, 1)
    result = []
    for subj in subjects:
        qs = Question.query.filter_by(subject=subj, is_active=True).all()
        if qs:
            batch = random.sample(qs, min(per_subject, len(qs)))
            result.extend(batch)
    random.shuffle(result)
    return [_q_to_dict(q) for q in result[:count]]


def get_weekly_questions(count: int = 40) -> list:
    from datetime import datetime
    year, week, _ = datetime.now().isocalendar()
    seed = year * 100 + week
    rng = random.Random(seed)
    subjects = ['physics', 'chemistry', 'biology', 'math']
    per_subject = max(count // 4, 1)
    result = []
    for subj in subjects:
        qs = Question.query.filter_by(subject=subj, is_active=True).all()
        if qs:
            batch = rng.sample(qs, min(per_subject, len(qs)))
            result.extend(batch)
    rng.shuffle(result)
    return [_q_to_dict(q) for q in result[:count]]


def get_smart_daily_questions(user_id: int, count: int = 20):
    """
    جلسة البناء اليومية الذكية:
    - تحلل آخر 20 اختبار للطالب
    - تحدد نقاط الضعف والقوة
    - تبني: 60% ضعيف + 30% متوسط + 10% قوي
    - تبدأ بمراجعة أخطاء آخر جلسة
    يُرجع: (list_of_questions, analysis_dict)
    """
    from models.evaluation import Evaluation

    subjects = ['physics', 'chemistry', 'biology', 'math']

    evals = (Evaluation.query
             .filter_by(user_id=user_id)
             .filter(Evaluation.subject.in_(subjects))
             .order_by(Evaluation.created_at.desc())
             .limit(20).all())

    if not evals:
        result = []
        per_subj = max(count // 4, 1)
        for subj in subjects:
            qs = Question.query.filter_by(subject=subj, is_active=True).all()
            if qs:
                result.extend(random.sample(qs, min(per_subj, len(qs))))
        random.shuffle(result)
        analysis = {
            'weak': [], 'medium': subjects, 'strong': [],
            'error_rates': {s: 50 for s in subjects},
            'review_count': 0, 'new_user': True,
        }
        return [_q_to_dict(q) for q in result[:count]], analysis

    subject_errors = {s: 0 for s in subjects}
    subject_total  = {s: 0 for s in subjects}
    wrong_ids_all  = set()
    review_ids     = []

    for i, ev in enumerate(evals):
        q_ids   = ev.get_questions_ids()
        answers = ev.get_user_answers()
        if not q_ids:
            continue
        questions = Question.query.filter(Question.id.in_(q_ids)).all()
        for q in questions:
            if q.subject not in subjects:
                continue
            subject_total[q.subject] += 1
            if answers.get(str(q.id), '').upper() != q.answer.upper():
                subject_errors[q.subject] += 1
                wrong_ids_all.add(q.id)
                if i == 0:
                    review_ids.append(q.id)

    error_rates = {}
    for s in subjects:
        if subject_total[s] > 0:
            error_rates[s] = subject_errors[s] / subject_total[s]
        else:
            error_rates[s] = 0.5

    sorted_subjs = sorted(error_rates.items(), key=lambda x: x[1], reverse=True)
    weak   = [s for s, r in sorted_subjs if r >= 0.45]
    medium = [s for s, r in sorted_subjs if 0.20 <= r < 0.45]
    strong = [s for s, r in sorted_subjs if r < 0.20]

    result   = []
    used_ids = set()

    review_limit = max(5, count // 8)
    review_sample = review_ids[:review_limit]
    if review_sample:
        review_qs = Question.query.filter(Question.id.in_(review_sample)).all()
        result.extend(review_qs)
        used_ids.update(q.id for q in review_qs)

    remaining    = count - len(result)
    weak_count   = int(remaining * 0.60)
    medium_count = int(remaining * 0.30)
    strong_count = remaining - weak_count - medium_count

    def _fetch_from(subj_list, n):
        if not subj_list or n <= 0:
            return []
        per = max(1, n // len(subj_list))
        out = []
        for subj in subj_list:
            exclude = used_ids | wrong_ids_all
            pool = Question.query.filter_by(subject=subj, is_active=True).filter(
                ~Question.id.in_(exclude)).all()
            if not pool:
                pool = Question.query.filter_by(subject=subj, is_active=True).filter(
                    ~Question.id.in_(used_ids)).all()
            batch = random.sample(pool, min(per, len(pool))) if pool else []
            out.extend(batch)
            used_ids.update(q.id for q in batch)
        return out[:n]

    fb = subjects
    result.extend(_fetch_from(weak   or fb, weak_count))
    result.extend(_fetch_from(medium or fb, medium_count))
    result.extend(_fetch_from(strong or fb, strong_count))

    if len(result) < count:
        need = count - len(result)
        pool = Question.query.filter_by(is_active=True).filter(
            ~Question.id.in_(used_ids)).all()
        result.extend(random.sample(pool, min(need, len(pool))))

    random.shuffle(result)

    analysis = {
        'weak':         weak,
        'medium':       medium,
        'strong':       strong,
        'error_rates':  {s: round(r * 100) for s, r in error_rates.items()},
        'review_count': len(review_sample),
        'new_user':     False,
    }
    return [_q_to_dict(q) for q in result[:count]], analysis


def get_daily_questions(subject: str, grade: str, day_number: int,
                        count: int, exclude_ids: list = None) -> list:
    if count <= 0:
        return []

    grade_db = GRADE_MAP.get(grade)
    exclude_ids = set(exclude_ids or [])

    # تحديد أولوية الصعوبة حسب رقم اليوم (تصعيد تدريجي)
    if day_number <= 5:
        priority = ['easy', 'medium', 'hard']
    elif day_number <= 10:
        priority = ['medium', 'easy', 'hard']
    elif day_number <= 15:
        priority = ['hard', 'medium', 'easy']
    else:
        priority = ['hard', 'medium', 'easy']

    def _fetch(diff, n, use_grade=True):
        q = Question.query.filter_by(subject=subject, is_active=True, difficulty=diff)
        if use_grade and grade_db:
            q = q.filter_by(grade=grade_db)
        qs = q.all()
        qs = [x for x in qs if x.id not in exclude_ids]
        return random.sample(qs, min(n, len(qs)))

    result = []
    remaining = count

    # جولة أولى: مع فلتر الصف والصعوبة
    for diff in priority:
        if remaining <= 0:
            break
        batch = _fetch(diff, remaining, use_grade=True)
        result.extend(batch)
        remaining -= len(batch)

    # جولة ثانية: مع فلتر الصعوبة بدون فلتر الصف (إذا لم تكتمل الكمية)
    if remaining > 0 and grade_db:
        for diff in priority:
            if remaining <= 0:
                break
            used = {x.id for x in result} | exclude_ids
            q = Question.query.filter_by(subject=subject, is_active=True, difficulty=diff)
            pool = [x for x in q.all() if x.id not in used]
            batch = random.sample(pool, min(remaining, len(pool)))
            result.extend(batch)
            remaining -= len(batch)

    # جولة ثالثة: أي سؤال متاح بدون قيود
    if remaining > 0:
        used = {x.id for x in result} | exclude_ids
        q = Question.query.filter_by(subject=subject, is_active=True)
        pool = [x for x in q.all() if x.id not in used]
        result.extend(random.sample(pool, min(remaining, len(pool))))

    return [_q_to_dict(q) for q in result]


def bulk_add_questions(questions_list: list, user_id: int) -> int:
    added = 0
    for q_data in questions_list:
        existing = Question.query.filter_by(
            text=q_data.get('text', ''),
            subject=q_data.get('subject', '')
        ).first()
        if existing:
            continue
        q = Question(
            text=q_data['text'],
            option_a=q_data['option_a'],
            option_b=q_data['option_b'],
            option_c=q_data['option_c'],
            option_d=q_data['option_d'],
            answer=q_data['answer'].upper(),
            explanation=q_data.get('explanation', ''),
            subject=q_data['subject'],
            difficulty=q_data.get('difficulty', 'medium'),
            lesson=q_data.get('lesson', ''),
            grade=q_data.get('grade', ''),
            chapter=q_data.get('chapter', ''),
            exam_type=q_data.get('exam_type', 'general'),
            created_by=user_id,
            source='seed'
        )
        db.session.add(q)
        added += 1
    db.session.commit()
    return added

def search_questions(keyword: str, subject: str = '', difficulty: str = '') -> list:
    q = Question.query.filter(Question.is_active == True)
    if keyword:
        q = q.filter(Question.text.contains(keyword))
    if subject:
        q = q.filter_by(subject=subject)
    if difficulty:
        q = q.filter_by(difficulty=difficulty)
    return q.limit(50).all()

def get_random_questions(subject: str, count: int = 10) -> list:
    qs = Question.query.filter_by(subject=subject, is_active=True).all()
    if len(qs) > count:
        qs = random.sample(qs, count)
    return qs
