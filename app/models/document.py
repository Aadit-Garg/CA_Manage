from datetime import datetime, timezone
from ..extensions import db

class Document(db.Model):
    """
    Metadata representation of a document stored in Cloudinary.
    """
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True) # Comma-separated tags
    document_type = db.Column(db.String(100), nullable=False, index=True) # e.g. GST Return, Income Tax Return
    financial_year = db.Column(db.String(20), nullable=False, index=True) # e.g. 2025-26
    
    # Cloudinary storage links
    cloudinary_public_id = db.Column(db.String(255), nullable=False)
    cloudinary_url = db.Column(db.String(255), nullable=False)
    
    # Metadata
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False) # In bytes
    file_hash = db.Column(db.String(64), nullable=True, index=True) # SHA-256 integrity check
    upload_version = db.Column(db.Integer, default=1, nullable=False)
    
    # Verification & Approval State
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved = db.Column(db.Boolean, default=False, nullable=False, index=True)
    status = db.Column(db.String(20), default='Active', nullable=False, index=True) # Active / Deleted (Soft Delete)
    
    # Security
    password_protected = db.Column(db.Boolean, default=False, nullable=False)
    pdf_password = db.Column(db.String(256), nullable=True) # Hashed password (never plain text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    client = db.relationship('ClientProfile', backref=db.backref('documents', cascade='all, delete-orphan', lazy='dynamic'))
    uploader = db.relationship('User', foreign_keys=[uploaded_by_id], backref='uploaded_documents')
    approver = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_documents')
    
    # sensible defaults for document types
    sensible_defaults = [
        'Income Tax Return',
        'GST Return',
        'Audit Report',
        'Balance Sheet',
        'Profit & Loss Statement',
        'Bank Statement',
        'Investment Report',
        'TDS Certificate',
        'Notice',
        'Invoice',
        'Other'
    ]

    def __repr__(self):
        return f'<Document {self.title} (version {self.upload_version})>'
