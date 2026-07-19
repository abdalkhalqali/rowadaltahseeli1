from extensions import db
from datetime import datetime, date

PRO_STANDARDS = {
    1:  {'name': 'معرفة طبيعة العلم وتاريخ تطور علم الفيزياء',                                        'type': 'physics'},
    2:  {'name': 'الإلمام بالمنهج العلمي وأخلاقياته وتطبيقاته في العلوم',                             'type': 'physics'},
    3:  {'name': 'إجراء التجارب العملية مع مراعاة قواعد السلامة والأمان في المختبر',                   'type': 'physics'},
    4:  {'name': 'تطبيق المهارات الرياضية والإحصائية',                                                 'type': 'physics'},
    5:  {'name': 'الإلمام بمبادئ ومفاهيم القوى وحركة الأجسام',                                        'type': 'physics'},
    6:  {'name': 'الإلمام بمبادئ ومفاهيم الموائع',                                                    'type': 'physics'},
    7:  {'name': 'تطبيق مبادئ ومفاهيم خواص المادة',                                                   'type': 'physics'},
    8:  {'name': 'الإلمام بمبادئ ومفاهيم الكهرباء الساكنة',                                           'type': 'physics'},
    9:  {'name': 'الإلمام بمبادئ ومفاهيم التيار الكهربائي والدوائر الكهربائية',                       'type': 'physics'},
    10: {'name': 'تطبيق مبادئ ومفاهيم المغناطيسية',                                                   'type': 'physics'},
    11: {'name': 'معرفة مبادئ ومفاهيم الحرارة والديناميكا الحرارية وتطبيقاتها',                       'type': 'physics'},
    12: {'name': 'وصف مبادئ ومفاهيم الموجات والاهتزازات وتطبيقاتها',                                  'type': 'physics'},
    13: {'name': 'معرفة مبادئ ومفاهيم الضوء',                                                         'type': 'physics'},
    14: {'name': 'الإلمام بمبادئ ومفاهيم الفيزياء الحديثة',                                           'type': 'physics'},
    15: {'name': 'الإلمام بمبادئ ومفاهيم الفيزياء النووية والإشعاعية',                                'type': 'physics'},
    16: {'name': 'معرفة علاقة علم الفيزياء بالعلوم الأخرى وتطبيقاتها في الحياة',                     'type': 'physics'},
    17: {'name': 'الإلمام بالمهارات الأساسية في تدريس الفيزياء والتوجهات الحديثة في التربية العلمية', 'type': 'educational'},
    18: {'name': 'الإلمام بطرق واستراتيجيات التدريس وأساليب التقويم الخاصة بالفيزياء',                'type': 'educational'},
}

class ProLicenseQuestion(db.Model):
    __tablename__ = 'pro_license_questions'

    id           = db.Column(db.Integer, primary_key=True)
    text         = db.Column(db.Text, nullable=False)
    option_a     = db.Column(db.String(500), nullable=False)
    option_b     = db.Column(db.String(500), nullable=False)
    option_c     = db.Column(db.String(500), nullable=False)
    option_d     = db.Column(db.String(500), nullable=False)
    answer       = db.Column(db.String(1), nullable=False)
    explanation  = db.Column(db.Text, default='')
    standard_num = db.Column(db.Integer, nullable=False)
    standard_name= db.Column(db.String(200), default='')
    q_type       = db.Column(db.String(20), default='educational')
    difficulty   = db.Column(db.String(20), default='medium')
    image_data   = db.Column(db.Text, default='')
    is_active    = db.Column(db.Boolean, default=True)
    has_drawing  = db.Column(db.Boolean, default=False)
    code_snippet = db.Column(db.Text, default='')
    code_type    = db.Column(db.String(20), default='python')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'text': self.text,
            'option_a': self.option_a, 'option_b': self.option_b,
            'option_c': self.option_c, 'option_d': self.option_d,
            'answer': self.answer, 'explanation': self.explanation,
            'standard_num': self.standard_num, 'standard_name': self.standard_name,
            'q_type': self.q_type, 'difficulty': self.difficulty,
            'image_data': self.image_data or '',
            'code_snippet': self.code_snippet or '',
            'code_type': self.code_type or 'python',
        }


class ProLicenseResult(db.Model):
    __tablename__ = 'pro_license_results'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    standard_num  = db.Column(db.Integer, nullable=True)
    questions_ids = db.Column(db.Text, default='[]')
    user_answers  = db.Column(db.Text, default='{}')
    score         = db.Column(db.Integer, default=0)
    total         = db.Column(db.Integer, default=0)
    exam_type     = db.Column(db.String(20), default='standard')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='pro_results')

    @property
    def score_pct(self):
        return round(self.score / self.total * 100) if self.total else 0


class DailyTrainingSession(db.Model):
    __tablename__ = 'daily_training_sessions'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    day_num       = db.Column(db.Integer, default=1)
    exam_date     = db.Column(db.Date, default=date.today)
    questions_ids = db.Column(db.Text, default='[]')
    review_ids    = db.Column(db.Text, default='[]')
    wrong_ids     = db.Column(db.Text, default='[]')
    score         = db.Column(db.Integer, default=0)
    total         = db.Column(db.Integer, default=0)
    completed     = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='daily_sessions')

    @property
    def score_pct(self):
        return round(self.score / self.total * 100) if self.total else 0
