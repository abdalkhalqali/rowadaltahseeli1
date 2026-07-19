from models import User
from extensions import db

SUBJECTS = ['physics', 'chemistry', 'biology', 'math']

def run_assessment(answers: dict) -> dict:
    results = {s: {'correct': 0, 'total': 0, 'pct': 0.0} for s in SUBJECTS}

    for q_id, answer_data in answers.items():
        subject     = answer_data.get('subject', '')
        is_correct  = answer_data.get('is_correct', False)

        if subject in results:
            results[subject]['total'] += 1
            if is_correct:
                results[subject]['correct'] += 1

    weak_subjects = []
    for s in SUBJECTS:
        total = results[s]['total']
        if total > 0:
            pct = (results[s]['correct'] / total) * 100
            results[s]['pct'] = round(pct, 1)
            if pct < 60:
                weak_subjects.append(s)
        else:
            results[s]['pct'] = 0.0

    total_correct = sum(r['correct'] for r in results.values())
    total_q       = sum(r['total']   for r in results.values())
    overall_pct   = round((total_correct / total_q) * 100, 1) if total_q else 0

    if overall_pct >= 80:
        level = 'advanced'
    elif overall_pct >= 55:
        level = 'intermediate'
    else:
        level = 'beginner'

    return {
        'subject_results': results,
        'weak_subjects':   weak_subjects,
        'overall_pct':     overall_pct,
        'total_correct':   total_correct,
        'total_q':         total_q,
        'level':           level,
    }

def save_assessment_results(user: User, results: dict):
    user.is_assessed   = True
    user.level         = results['level']
    user.set_weak_points_list(results['weak_subjects'])

    from models import Evaluation
    ev = Evaluation(
        user_id=user.id,
        eval_type='assessment',
        subject='mixed',
        exam_type='level_assessment',
        grade=user.grade,
        total_q=results['total_q'],
        correct=results['total_correct'],
        score_pct=results['overall_pct']
    )
    db.session.add(ev)
    user.total_score += results['total_correct']
    user.exams_taken += 1
    db.session.commit()
