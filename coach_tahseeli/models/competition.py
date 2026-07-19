from extensions import db
from datetime import datetime
import json

class Competition(db.Model):
    __tablename__ = 'competitions'

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(200), nullable=False)
    subject          = db.Column(db.String(30), nullable=False)
    description      = db.Column(db.Text, default='')
    duration_min     = db.Column(db.Integer, default=30)
    total_q          = db.Column(db.Integer, default=20)
    difficulty       = db.Column(db.String(20), default='mixed')
    status           = db.Column(db.String(20), default='upcoming')
    start_time       = db.Column(db.DateTime, nullable=True)
    end_time         = db.Column(db.DateTime, nullable=True)
    created_by       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    questions_ids    = db.Column(db.Text, default='[]')
    max_participants = db.Column(db.Integer, default=100)
    prize            = db.Column(db.String(200), default='')

    participants = db.relationship('CompetitionParticipant', backref='competition', lazy=True)

    def get_questions_ids(self):
        try:
            return json.loads(self.questions_ids)
        except Exception:
            return []

    @property
    def participant_count(self):
        return len(self.participants)

    @property
    def is_joinable(self):
        return self.status in ('upcoming', 'active') and self.participant_count < self.max_participants

    @property
    def subject_ar(self):
        mapping = {
            'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
            'biology': 'الأحياء',  'math': 'الرياضيات',
            'mixed':   'مختلطة'
        }
        return mapping.get(self.subject, self.subject)

    def __repr__(self):
        return f'<Competition {self.name}>'


class CompetitionParticipant(db.Model):
    __tablename__ = 'competition_participants'

    id             = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score          = db.Column(db.Integer, default=0)
    correct        = db.Column(db.Integer, default=0)
    total_q        = db.Column(db.Integer, default=0)
    time_taken     = db.Column(db.Integer, default=0)
    rank           = db.Column(db.Integer, default=0)
    submitted      = db.Column(db.Boolean, default=False)
    answers        = db.Column(db.Text, default='{}')
    joined_at      = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at    = db.Column(db.DateTime, nullable=True)

    def get_answers(self):
        try:
            return json.loads(self.answers)
        except Exception:
            return {}
