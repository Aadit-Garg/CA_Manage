import os
from hashlib import sha256
from flask import current_app
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader

def _get_cloudinary_config():
    """Dynamically fetch configuration from Flask current_app."""
    return {
        'cloud_name': current_app.config.get('CLOUDINARY_CLOUD_NAME'),
        'api_key': current_app.config.get('CLOUDINARY_API_KEY'),
        'api_secret': current_app.config.get('CLOUDINARY_API_SECRET'),
        'secure': True
    }

def upload_pdf(file_storage):
    """
    Upload a PDF FileStorage object to Cloudinary.
    Enforces PDF validation, size restriction (25MB), sanitization, and SHA-256 hash generation.
    Returns:
        Dict with keys: cloudinary_public_id, cloudinary_url, original_filename, file_size, file_hash
    """
    # 1. Enforce size restriction (25MB = 26,214,400 bytes)
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)
    
    if file_size > 25 * 1024 * 1024:
        raise ValueError("File exceeds maximum allowed size of 25MB.")
    
    # 2. Enforce PDF MIME and Extension validation
    filename = secure_filename(file_storage.filename)
    if not filename.lower().endswith('.pdf'):
        raise ValueError("Only PDF files are allowed.")
    
    # Check mimetype
    if file_storage.content_type != 'application/pdf':
        raise ValueError("Invalid file format. Uploaded file is not a valid PDF.")
    
    # 3. Generate SHA-256 hash for duplicate check
    sha = sha256()
    while chunk := file_storage.read(8192):
        sha.update(chunk)
    file_hash = sha.hexdigest()
    file_storage.seek(0)

    # 4. Upload to Cloudinary under folder "ca_manage_docs"
    config = _get_cloudinary_config()
    upload_result = cloudinary.uploader.upload(
        file_storage,
        folder="ca_manage_docs",
        resource_type="raw", # Crucial: raw resource preserves original PDF bytes exactly
        use_filename=True,
        unique_filename=True,
        **config
    )

    return {
        'cloudinary_public_id': upload_result['public_id'],
        'cloudinary_url': upload_result['secure_url'],
        'original_filename': filename,
        'file_size': file_size,
        'file_hash': file_hash
    }

def delete_pdf(public_id):
    """Delete a raw PDF resource from Cloudinary."""
    config = _get_cloudinary_config()
    cloudinary.uploader.destroy(public_id, resource_type="raw", **config)
