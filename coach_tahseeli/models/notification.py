from extensions import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title      = db.Column(db.String(200), nullable=False)
    body       = db.Column(db.Text, default='')
    notif_type = db.Column(db.String(30), default='system')  # system | admin | achievement
    is_read    = db.Column(db.Boolean, default=False)
    link       = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user   = db.relationship('User', foreign_keys=[user_id],  backref='notifications')
    sender = db.relationship('User', foreign_keys=[sender_id])

    @property
    def icon(self):
        return {'admin': '📢', 'achievement': '🏆', 'system': 'ℹ️'}.get(self.notif_type, 'ℹ️')

    def __repr__(self):
        return f'<Notification {self.id}: {self.title[:30]}>'
