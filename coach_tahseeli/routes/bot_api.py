"""
Bot API — يُتيح للبوت المستقل قراءة الأسئلة والإحصائيات من المنصة
محمي بـ BOT_API_KEY
"""
import os
from flask import Blueprint, request, jsonify
from extensions import db
from models.question import Question

bot_api_bp = Blueprint('bot_api', __name__)


def _auth():
    """التحقق من مفتاح API"""
    key = os.environ.get('BOT_API_KEY', '')
    if not key:
        return True  # إذا لم يُضبط المفتاح → مفتوح (للتطوير)
    sent = request.headers.get('X-Bot-Key') or request.args.get('key', '')
    return sent == key


@bot_api_bp.route('/questions')
def questions():
    if not _auth():
        return jsonify({'error': 'unauthorized'}), 401

    subject   = request.args.get('subject')
    exam_type = request.args.get('exam_type')
    source    = request.args.get('source')
    grade     = request.args.get('grade')
    limit     = min(int(request.args.get('limit', 10)), 100)

    q = Question.query.filter_by(is_active=True)

    if subject:
        q = q.filter_by(subject=subject)
    if grade:
        q = q.filter_by(grade=str(grade))
    if source:
        if source == 'prev':
            q = q.filter(Question.source.like('prev_%'))
        else:
            q = q.filter_by(source=source)
    elif exam_type:
        if exam_type == 'final_test':
            q = q.filter(Question.exam_type.in_(['final_test', 'chapter_1', 'chapter_2']))
        elif exam_type not in ('daily_train', 'level_test', 'quick_test'):
            q = q.filter_by(exam_type=exam_type)

    rows = q.order_by(db.func.random()).limit(limit).all()

    # إذا لم نجد بـ source → جرّب بدونه
    if not rows and source:
        q2 = Question.query.filter_by(is_active=True)
        if subject:   q2 = q2.filter_by(subject=subject)
        if grade:     q2 = q2.filter_by(grade=str(grade))
        if exam_type and exam_type not in ('daily_train', 'level_test', 'quick_test'):
            q2 = q2.filter_by(exam_type=exam_type)
        rows = q2.order_by(db.func.random()).limit(limit).all()

    def _row(r):
        return {
            'id':        r.id,
            'subject':   r.subject,
            'exam_type': r.exam_type,
            'grade':     r.grade,
            'source':    r.source,
            'question':  r.text,
            'option_a':  r.option_a,
            'option_b':  r.option_b,
            'option_c':  r.option_c,
            'option_d':  r.option_d,
            'answer':    r.answer,
            'explanation': r.explanation or '',
        }

    return jsonify([_row(r) for r in rows])


@bot_api_bp.route('/grades')
def grades():
    if not _auth():
        return jsonify({'error': 'unauthorized'}), 401

    subject = request.args.get('subject')
    q = db.session.query(Question.grade).filter(
        Question.is_active == True,
        Question.grade.isnot(None)
    )
    if subject:
        q = q.filter(Question.subject == subject)
    result = sorted({r[0] for r in q.distinct().all() if r[0]})
    return jsonify(result)


@bot_api_bp.route('/count')
def count():
    if not _auth():
        return jsonify({'error': 'unauthorized'}), 401

    subject = request.args.get('subject')
    grade   = request.args.get('grade')
    q = Question.query.filter_by(is_active=True)
    if subject: q = q.filter_by(subject=subject)
    if grade:   q = q.filter_by(grade=str(grade))
    return jsonify({'count': q.count()})


@bot_api_bp.route('/stats')
def stats():
    if not _auth():
        return jsonify({'error': 'unauthorized'}), 401

    from models.user import User
    from models.evaluation import Evaluation
    try:
        q_count = Question.query.filter_by(is_active=True).count()
        u_count = User.query.filter_by(is_admin=False).count()
        e_count = Evaluation.query.count()
        return jsonify({'questions': q_count, 'students': u_count, 'exams': e_count})
    except Exception as e:
        return jsonify({'questions': 0, 'students': 0, 'exams': 0})
