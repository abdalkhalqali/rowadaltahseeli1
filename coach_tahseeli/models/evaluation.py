from extensions import db
from datetime import datetime
import json

class Evaluation(db.Model):
    __tablename__ = 'evaluations'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    eval_type     = db.Column(db.String(30), default='exam')
    subject       = db.Column(db.String(30), nullable=False)
    exam_type     = db.Column(db.String(30), default='general')
    grade         = db.Column(db.String(20), default='grade_12')
    total_q       = db.Column(db.Integer, default=0)
    correct       = db.Column(db.Integer, default=0)
    score_pct     = db.Column(db.Float, default=0.0)
    time_taken    = db.Column(db.Integer, default=0)
    questions_ids = db.Column(db.Text, default='[]')
    user_answers  = db.Column(db.Text, default='{}')
    analysis      = db.Column(db.Text, default='')
    recommendations = db.Column(db.Text, default='')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def get_questions_ids(self):
        try:
            return json.loads(self.questions_ids)
        except Exception:
            return []

    def get_user_answers(self):
        try:
            return json.loads(self.user_answers)
        except Exception:
            return {}

    def set_user_answers(self, d):
        self.user_answers = json.dumps(d, ensure_ascii=False)

    def set_questions_ids(self, lst):
        self.questions_ids = json.dumps(lst)

    @property
    def grade_label(self):
        if self.score_pct >= 90:
            return ('ممتاز', 'success')
        elif self.score_pct >= 75:
            return ('جيد جداً', 'info')
        elif self.score_pct >= 60:
            return ('جيد', 'warning')
        elif self.score_pct >= 50:
            return ('مقبول', 'secondary')
        else:
            return ('بحاجة لمراجعة', 'danger')

    def __repr__(self):
        return f'<Evaluation {self.id}: {self.subject} {self.score_pct}%>'
