from datetime import datetime, timezone
from ..extensions import db

class PushSubscription(db.Model):
    """
    Stores Web Push API subscriptions for users.
    A user can have multiple subscriptions if they use multiple browsers/devices.
    """
    __tablename__ = 'push_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<PushSubscription {self.id} for User {self.user_id}>'
