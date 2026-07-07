from datetime import datetime, timezone
from ..extensions import db

class SavedFilter(db.Model):
    """
    User-saved dashboard or search filters.
    """
    __tablename__ = 'saved_filters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(50), nullable=False) # e.g. 'search', 'attendance', 'approvals'
    filter_json = db.Column(db.JSON, nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship('User', backref=db.backref('saved_filters', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<SavedFilter {self.name} for User {self.user_id}>'
