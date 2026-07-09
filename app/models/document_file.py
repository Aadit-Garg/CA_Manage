from datetime import datetime, timezone
from ..extensions import db

class DocumentFile(db.Model):
    """
    Represents an individual PDF file attached to a Document.
    """
    __tablename__ = 'document_files'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Custom name for this specific file (e.g. "Computation", "Acknowledgement")
    name = db.Column(db.String(255), nullable=False)
    
    # Cloudinary storage links
    cloudinary_public_id = db.Column(db.String(255), nullable=False)
    cloudinary_url = db.Column(db.String(255), nullable=False)
    
    # Metadata
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False) # In bytes
    file_hash = db.Column(db.String(64), nullable=True) # SHA-256 integrity check
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document = db.relationship('Document', backref=db.backref('files', cascade='all, delete-orphan', order_by=created_at.asc()))

    def __repr__(self):
        return f'<DocumentFile {self.id} for Document {self.document_id}>'
