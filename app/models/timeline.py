from datetime import datetime, timezone
from ..extensions import db

class TimelineEvent(db.Model):
    """
    Chronological record of important actions and events associated with a client.
    Visible to Admins (full) and Employees (read-only).
    """
    __tablename__ = 'timeline_events'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    event_type = db.Column(db.String(100), nullable=False, index=True) # e.g. Client Created, Document Uploaded
    description = db.Column(db.Text, nullable=False)
    
    # Optional relationships for richer context
    performed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    client = db.relationship('ClientProfile', backref=db.backref('timeline_events', lazy='dynamic', cascade='all, delete-orphan', order_by='desc(TimelineEvent.created_at)'))
    performed_by = db.relationship('User', foreign_keys=[performed_by_id])
    document = db.relationship('Document', foreign_keys=[document_id])

    def __repr__(self):
        return f'<TimelineEvent {self.event_type} for Client {self.client_id}>'
