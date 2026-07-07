from datetime import datetime, timezone
from ..extensions import db

class AuditLog(db.Model):
    """
    Immutable audit log for tracking system events and modifications.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    user_role = db.Column(db.String(50), nullable=True) # e.g., 'admin', 'employee', 'client', 'system'
    
    action = db.Column(db.String(100), nullable=False, index=True) # e.g., 'login', 'create_client', 'delete_document'
    module = db.Column(db.String(100), nullable=False, index=True) # e.g., 'auth', 'clients', 'documents', 'attendance'
    
    entity_type = db.Column(db.String(100), nullable=True) # e.g., 'ClientProfile', 'Document'
    entity_id = db.Column(db.String(100), nullable=True)
    
    description = db.Column(db.Text, nullable=False)
    
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationship
    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_role} at {self.created_at}>'
