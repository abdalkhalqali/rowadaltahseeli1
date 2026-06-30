from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password      = db.Column(db.String(256), nullable=False)
    gender        = db.Column(db.String(10), default='unknown')
    grade         = db.Column(db.String(20), default='grade_12')
    level         = db.Column(db.String(20), default='unknown')
    weak_points   = db.Column(db.Text, default='')
    is_admin      = db.Column(db.Boolean, default=False)
    is_verified   = db.Column(db.Boolean, default=False)
    is_assessed   = db.Column(db.Boolean, default=False)
    otp_code      = db.Column(db.String(6), nullable=True)
    otp_expires   = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)
    total_score   = db.Column(db.Integer, default=0)
    exams_taken   = db.Column(db.Integer, default=0)
    streak_days   = db.Column(db.Integer, default=0)
    is_banned     = db.Column(db.Boolean, default=False)
    plain_password= db.Column(db.String(256), nullable=True)
    bio           = db.Column(db.Text, default='')
    admin_role    = db.Column(db.String(30), default='')
    perm_questions         = db.Column(db.Boolean, default=False)
    perm_users             = db.Column(db.Boolean, default=False)
    perm_community         = db.Column(db.Boolean, default=False)
    perm_analytics         = db.Column(db.Boolean, default=False)
    perm_notifications     = db.Column(db.Boolean, default=False)
    perm_lectures          = db.Column(db.Boolean, default=False)
    receive_lecture_notifs = db.Column(db.Boolean, default=True)
    receive_exam_notifs    = db.Column(db.Boolean, default=True)

    evaluations   = db.relationship('Evaluation', backref='student', lazy=True,
                                    foreign_keys='Evaluation.user_id')
    competitions  = db.relationship('CompetitionParticipant', backref='user', lazy=True)

    def get_weak_points_list(self):
        import json
        try:
            return json.loads(self.weak_points) if self.weak_points else []
        except Exception:
            return []

    def set_weak_points_list(self, lst):
        import json
        self.weak_points = json.dumps(lst, ensure_ascii=False)

    @property
    def average_score(self):
        if self.exams_taken == 0:
            return 0
        return round(self.total_score / self.exams_taken, 1)

    def __repr__(self):
        return f'<User {self.name}>'
