from extensions import db
from datetime import datetime, timedelta

REACTION_EMOJIS = ['🔥', '❤️', '👏', '💡', '😮', '🎯', '💪', '⭐']

class StoryReaction(db.Model):
    __tablename__ = 'story_reactions'
    id         = db.Column(db.Integer, primary_key=True)
    story_id   = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji      = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('story_id', 'user_id', name='uq_reaction'),)
    user  = db.relationship('User', backref='story_reactions')

class Story(db.Model):
    __tablename__ = 'stories'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text       = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(300), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.utcnow() + timedelta(hours=24))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='stories')
    views  = db.relationship('StoryView', backref='story',
                             lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_active(self):
        return datetime.utcnow() < self.expires_at

    @property
    def view_count(self):
        return self.views.count()

    def has_viewed(self, user_id):
        return self.views.filter_by(viewer_id=user_id).first() is not None


class StoryView(db.Model):
    __tablename__ = 'story_views'

    id         = db.Column(db.Integer, primary_key=True)
    story_id   = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    viewer_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_at  = db.Column(db.DateTime, default=datetime.utcnow)

    viewer = db.relationship('User', backref='story_views')
