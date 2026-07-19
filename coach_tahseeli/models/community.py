from extensions import db
from datetime import datetime

class CommunityPost(db.Model):
    __tablename__ = 'community_posts'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body       = db.Column(db.Text, nullable=False)
    post_type  = db.Column(db.String(20), default='general')  # general | question | achievement
    likes      = db.Column(db.Integer, default=0)
    is_pinned  = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    parent_id  = db.Column(db.Integer, db.ForeignKey('community_posts.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author  = db.relationship('User', backref='community_posts')
    replies = db.relationship('CommunityPost',
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic',
                              foreign_keys=[parent_id])

    @property
    def type_label(self):
        return {'general': '💬 نقاش', 'question': '❓ سؤال',
                'achievement': '🏆 إنجاز'}.get(self.post_type, '💬')

    @property
    def reply_count(self):
        return self.replies.filter_by(is_deleted=False).count()

    def __repr__(self):
        return f'<CommunityPost {self.id}: {self.body[:30]}>'
