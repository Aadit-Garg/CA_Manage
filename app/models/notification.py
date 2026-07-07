from datetime import datetime, timezone
from ..extensions import db

class Notification(db.Model):
    """
    In-app notifications for users (Admins, Employees, or Clients).
    """
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = db.Column(db.String(100), nullable=True) # e.g. 'Approval Required'
    message = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=True, default='system') # system, approval, client, attendance
    priority = db.Column(db.String(20), nullable=True, default='normal') # low, normal, high
    
    entity_type = db.Column(db.String(100), nullable=True) # e.g. 'ApprovalRequest'
    entity_id = db.Column(db.Integer, nullable=True)
    
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan', order_by='desc(Notification.created_at)'))

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'
