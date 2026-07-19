from extensions import db
from datetime import datetime


class ContentSection(db.Model):
    __tablename__ = 'cms_sections'

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(200), nullable=False)
    icon         = db.Column(db.String(10), default='📁')
    parent_id    = db.Column(db.Integer, db.ForeignKey('cms_sections.id'), nullable=True)
    order_num    = db.Column(db.Integer, default=0)
    link         = db.Column(db.String(500), default='')
    fallback_msg = db.Column(db.Text, default='')
    description  = db.Column(db.Text, default='')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    parent   = db.relationship('ContentSection', remote_side=[id], backref='children')
    files    = db.relationship('ContentFile', backref='section', lazy='dynamic', cascade='all, delete-orphan')
    codes    = db.relationship('ContentCode', backref='section', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def children_sorted(self):
        return sorted(self.children, key=lambda s: s.order_num)

    def to_dict(self, include_children=True):
        d = {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'parent_id': self.parent_id,
            'order_num': self.order_num,
            'link': self.link,
            'fallback_msg': self.fallback_msg,
            'description': self.description,
            'file_count': self.files.filter_by(is_active=True).count(),
            'code_count': self.codes.filter_by(is_active=True).count(),
        }
        if include_children:
            d['children'] = [c.to_dict(include_children=True) for c in self.children_sorted]
        return d


class ContentFile(db.Model):
    __tablename__ = 'cms_files'

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(300), nullable=False)
    section_id   = db.Column(db.Integer, db.ForeignKey('cms_sections.id'), nullable=True)
    file_path    = db.Column(db.String(500), default='')
    file_url     = db.Column(db.String(500), default='')
    file_type    = db.Column(db.String(20), default='pdf')
    file_size    = db.Column(db.Integer, default=0)
    ai_topic     = db.Column(db.String(200), default='')
    ai_keywords  = db.Column(db.Text, default='')
    ai_summary   = db.Column(db.Text, default='')
    ai_difficulty= db.Column(db.String(30), default='')
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'section_id': self.section_id,
            'section_name': self.section.name if self.section else '',
            'file_url': self.file_url,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'ai_topic': self.ai_topic,
            'ai_keywords': self.ai_keywords,
            'ai_summary': self.ai_summary,
            'ai_difficulty': self.ai_difficulty,
            'created_at': self.created_at.strftime('%Y-%m-%d'),
        }


class ContentCode(db.Model):
    __tablename__ = 'cms_codes'

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(300), nullable=False)
    section_id    = db.Column(db.Integer, db.ForeignKey('cms_sections.id'), nullable=True)
    code_type     = db.Column(db.String(20), default='python')
    difficulty    = db.Column(db.String(20), default='medium')
    description   = db.Column(db.Text, default='')
    code_content  = db.Column(db.Text, default='')
    external_url  = db.Column(db.String(500), default='')
    questions_json= db.Column(db.Text, default='[]')
    ai_topic      = db.Column(db.String(200), default='')
    ai_keywords   = db.Column(db.Text, default='')
    ai_summary    = db.Column(db.Text, default='')
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'section_id': self.section_id,
            'section_name': self.section.name if self.section else '',
            'code_type': self.code_type,
            'difficulty': self.difficulty,
            'description': self.description,
            'code_content': self.code_content,
            'external_url': self.external_url,
            'questions_json': self.questions_json,
            'ai_topic': self.ai_topic,
            'ai_keywords': self.ai_keywords,
            'ai_summary': self.ai_summary,
            'created_at': self.created_at.strftime('%Y-%m-%d'),
        }
