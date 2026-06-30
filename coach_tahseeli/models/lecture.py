from extensions import db
from datetime import datetime
import re

class Lecture(db.Model):
    __tablename__ = 'lectures'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    channel     = db.Column(db.String(100), default='')
    video_url   = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, default='')
    standard    = db.Column(db.String(200), default='')
    subject     = db.Column(db.String(50), default='')
    branch      = db.Column(db.String(30), nullable=False)
    section     = db.Column(db.String(30), default='')
    order_num   = db.Column(db.Integer, default=0)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    views_real  = db.Column(db.Integer, default=0)
    views_fake  = db.Column(db.Integer, default=0)
    transcript  = db.Column(db.Text, default='')

    feedbacks   = db.relationship('LectureFeedback', backref='lecture', lazy='dynamic')

    def embed_url(self):
        url = self.video_url.strip()
        # Google Drive
        gdrive = re.search(r'drive\.google\.com/file/d/([^/\?]+)', url)
        if gdrive:
            return f'https://drive.google.com/file/d/{gdrive.group(1)}/preview'
        # YouTube
        yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\?/]+)', url)
        if yt:
            return (f'https://www.youtube.com/embed/{yt.group(1)}'
                    f'?rel=0&modestbranding=1&controls=0'
                    f'&disablekb=1&fs=0&iv_load_policy=3'
                    f'&cc_load_policy=0&showinfo=0&playsinline=1'
                    f'&enablejsapi=1')
        # Telegram (قناة عامة)
        tg = re.search(r't\.me/([^/\s]+)/(\d+)', url)
        if tg:
            return f'https://t.me/{tg.group(1)}/{tg.group(2)}?embed=1&mode=tme'
        return url

    def gdrive_file_id(self):
        url = self.video_url.strip()
        m = re.search(r'drive\.google\.com/file/d/([^/\?]+)', url)
        return m.group(1) if m else None

    def video_src(self):
        """رابط الفيديو المباشر للعنصر <video> (روابط مباشرة فقط)"""
        return self.video_url.strip()

    def is_youtube(self):
        url = self.video_url.strip()
        return bool(re.search(r'(?:youtube\.com|youtu\.be)', url))

    def is_gdrive(self):
        url = self.video_url.strip()
        return bool(re.search(r'drive\.google\.com', url))

    def is_telegram(self):
        url = self.video_url.strip()
        return bool(re.search(r't\.me/[^/\s]+/\d+', url))

    def is_iframe_only(self):
        """مصادر لا يمكن التحكم بها من خارج الـ iframe"""
        return self.is_gdrive() or self.is_telegram()

    @property
    def total_views(self):
        return (self.views_real or 0) + (self.views_fake or 0)

    def __repr__(self):
        return f'<Lecture {self.id}: {self.title}>'


class LectureView(db.Model):
    """تتبع مشاهدات كل مستخدم لكل محاضرة"""
    __tablename__ = 'lecture_views'

    id          = db.Column(db.Integer, primary_key=True)
    lecture_id  = db.Column(db.Integer, db.ForeignKey('lectures.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    first_seen  = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    watch_secs  = db.Column(db.Integer,  default=0)   # ثواني المشاهدة المتراكمة
    completed   = db.Column(db.Boolean,  default=False)

    lecture = db.relationship('Lecture',  backref=db.backref('views_log', lazy='dynamic'))
    user    = db.relationship('User',     backref=db.backref('lecture_views', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('lecture_id', 'user_id', name='uq_lecture_user'),
    )

    def __repr__(self):
        return f'<LectureView lecture={self.lecture_id} user={self.user_id}>'


class LectureFeedback(db.Model):
    __tablename__ = 'lecture_feedback'

    id                  = db.Column(db.Integer, primary_key=True)
    lecture_id          = db.Column(db.Integer, db.ForeignKey('lectures.id'), nullable=False)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    learned             = db.Column(db.Text, default='')
    needs_clarification = db.Column(db.Text, default='')
    rating              = db.Column(db.Integer, default=5)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='lecture_feedbacks')

    def __repr__(self):
        return f'<LectureFeedback {self.id}: lecture={self.lecture_id}>'
