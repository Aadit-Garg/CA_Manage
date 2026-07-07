from datetime import datetime, timezone
from ..extensions import db

class DocumentVersion(db.Model):
    """
    History log for document versions to keep previous replacements.
    """
    __tablename__ = 'document_versions'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    
    cloudinary_public_id = db.Column(db.String(255), nullable=False)
    cloudinary_url = db.Column(db.String(255), nullable=False)
    
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document = db.relationship('Document', backref=db.backref('versions', cascade='all, delete-orphan', order_by=version_number.desc()))
    uploader = db.relationship('User', backref='uploaded_versions')

    def __repr__(self):
        return f'<DocumentVersion {self.document_id} v{self.version_number}>'
