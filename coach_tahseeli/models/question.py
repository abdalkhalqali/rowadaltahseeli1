from extensions import db
from datetime import datetime

class Question(db.Model):
    __tablename__ = 'questions'

    id          = db.Column(db.Integer, primary_key=True)
    text        = db.Column(db.Text, nullable=False)
    option_a    = db.Column(db.String(300), nullable=False)
    option_b    = db.Column(db.String(300), nullable=False)
    option_c    = db.Column(db.String(300), nullable=False)
    option_d    = db.Column(db.String(300), nullable=False)
    answer      = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text, default='')
    subject     = db.Column(db.String(30), nullable=False)
    difficulty  = db.Column(db.String(20), default='medium')
    lesson      = db.Column(db.String(100), default='')
    grade       = db.Column(db.String(20), default='grade_12')
    chapter     = db.Column(db.String(50), default='')
    exam_type   = db.Column(db.String(30), default='general')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active   = db.Column(db.Boolean, default=True)
    source      = db.Column(db.String(50), default='manual')
    image_path    = db.Column(db.String(300), default='')
    code_snippet  = db.Column(db.Text, default='')
    code_type     = db.Column(db.String(20), default='python')

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'options': {'A': self.option_a, 'B': self.option_b,
                        'C': self.option_c, 'D': self.option_d},
            'answer': self.answer,
            'explanation': self.explanation,
            'subject': self.subject,
            'difficulty': self.difficulty,
            'lesson': self.lesson,
            'chapter': self.chapter,
            'grade': self.grade,
            'exam_type': self.exam_type,
            'image_path': self.image_path or '',
            'code_snippet': self.code_snippet or '',
            'code_type': self.code_type or 'python',
        }

    def __repr__(self):
        return f'<Question {self.id}: {self.subject}>'
