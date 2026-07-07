from datetime import datetime, timezone
from ..extensions import db

class UploadSession(db.Model):
    """
    Tracks a bulk upload session by an administrator or employee.
    """
    __tablename__ = 'upload_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False) # 'admin' or 'employee'
    
    total_files = db.Column(db.Integer, default=0, nullable=False)
    successful_uploads = db.Column(db.Integer, default=0, nullable=False)
    failed_uploads = db.Column(db.Integer, default=0, nullable=False)
    duplicate_files = db.Column(db.Integer, default=0, nullable=False)
    unknown_clients = db.Column(db.Integer, default=0, nullable=False)
    approval_requests_created = db.Column(db.Integer, default=0, nullable=False)
    
    time_taken_seconds = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('upload_sessions', lazy=True, cascade="all, delete-orphan"))
    files = db.relationship('UploadSessionFile', backref='session', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<UploadSession {self.id} ({self.total_files} files)>'


class UploadSessionFile(db.Model):
    """
    Tracks individual files processed during a bulk upload session.
    """
    __tablename__ = 'upload_session_files'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('upload_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False) # 'Success', 'Failed', 'Duplicate', 'Skipped', 'Pending Approval'
    error_message = db.Column(db.Text, nullable=True)
    
    # Optional links to the created document or matched client
    client_id = db.Column(db.Integer, db.ForeignKey('client_profiles.id', ondelete='SET NULL'), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    approval_request_id = db.Column(db.Integer, db.ForeignKey('approval_requests.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    client = db.relationship('ClientProfile')
    document = db.relationship('Document')
    approval_request = db.relationship('ApprovalRequest')

    def __repr__(self):
        return f'<UploadSessionFile {self.filename} - {self.status}>'
