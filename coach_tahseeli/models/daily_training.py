from extensions import db
from datetime import datetime, date
import json


class DailyTraining(db.Model):
    __tablename__ = 'daily_training'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject        = db.Column(db.String(30), nullable=False)
    grade          = db.Column(db.String(20), default='')
    training_date  = db.Column(db.Date, nullable=False, default=date.today)
    day_number     = db.Column(db.Integer, default=1)
    questions_ids  = db.Column(db.Text, default='[]')
    wrong_ids      = db.Column(db.Text, default='[]')
    repeated_ids   = db.Column(db.Text, default='[]')
    total_q        = db.Column(db.Integer, default=0)
    correct        = db.Column(db.Integer, default=0)
    score_pct      = db.Column(db.Float, default=0.0)
    completed      = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('daily_trainings', lazy=True))

    def get_questions_ids(self):
        try:
            return json.loads(self.questions_ids)
        except Exception:
            return []

    def set_questions_ids(self, lst):
        self.questions_ids = json.dumps(lst)

    def get_wrong_ids(self):
        try:
            return json.loads(self.wrong_ids)
        except Exception:
            return []

    def set_wrong_ids(self, lst):
        self.wrong_ids = json.dumps(lst)

    def get_repeated_ids(self):
        try:
            return json.loads(self.repeated_ids)
        except Exception:
            return []

    def set_repeated_ids(self, lst):
        self.repeated_ids = json.dumps(lst)

    @staticmethod
    def get_last_session(user_id, subject):
        return (DailyTraining.query
                .filter_by(user_id=user_id, subject=subject)
                .order_by(DailyTraining.training_date.desc())
                .first())

    @staticmethod
    def count_absences(user_id, subject):
        sessions = (DailyTraining.query
                    .filter_by(user_id=user_id, subject=subject, completed=True)
                    .order_by(DailyTraining.training_date.asc())
                    .all())
        if len(sessions) < 2:
            return 0
        absences = 0
        for i in range(1, len(sessions)):
            gap = (sessions[i].training_date - sessions[i - 1].training_date).days
            if gap > 1:
                absences += gap - 1
        return absences

    @staticmethod
    def get_next_day_number(user_id, subject):
        last = DailyTraining.get_last_session(user_id, subject)
        if not last or not last.completed:
            return 1
        return last.day_number + 1

    def __repr__(self):
        return f'<DailyTraining {self.id}: user={self.user_id} {self.subject} day={self.day_number}>'
