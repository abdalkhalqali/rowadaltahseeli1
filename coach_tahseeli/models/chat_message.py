from extensions import db
from datetime import datetime

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role       = db.Column(db.String(20), default='user')   # user | assistant | system
    content    = db.Column(db.Text, nullable=False)
    lecture_id = db.Column(db.Integer, nullable=True)       # if chat about a specific lecture
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='chat_messages')
