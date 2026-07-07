import re
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from ..extensions import db
from ..models.client import ClientProfile
from ..models.document import Document
from ..models.approval import ApprovalRequest
from ..models.upload_session import UploadSession, UploadSessionFile
from ..utils.cloudinary_helper import upload_pdf
from . import api_bp
from ..auth.decorators import role_required
from functools import wraps

def admin_or_employee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'employee']:
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/bulk-upload/analyze', methods=['POST'])
@admin_or_employee_required
def analyze_bulk_upload():
    """
    Receives metadata of files (filename, size, hash) and validates them.
    Returns the mapped client info and validation status.
    """
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Invalid payload format'}), 400

    clients = ClientProfile.query.filter_by(status='Active').all()
    
    # Pre-build mapping for O(1) matching
    upload_id_map = {}
    for c in clients:
        if c.upload_id:
            upload_id_map[c.upload_id.lower()] = c

    # Also build a set of existing file hashes/names for duplicate detection
    existing_docs = Document.query.with_entities(Document.file_hash, Document.original_filename).all()
    existing_hashes = {d[0] for d in existing_docs if d[0]}
    existing_filenames = {d[1].lower() for d in existing_docs if d[1]}
    
    results = []
    
    for file_meta in data:
        filename = file_meta.get('filename', '')
        size = file_meta.get('size', 0)
        file_hash = file_meta.get('hash', '')
        
        lower_name = filename.lower()
        matched_client = None
        
        # 1. Match Client
        for uid_lower, client in upload_id_map.items():
            # Match UUID disregarding surrounding dash/spaces
            if uid_lower in lower_name:
                matched_client = client
                break
                
        # 2. Guess Document Type
        doc_type = "Other"
        types = ["Income Tax Return", "GST Return", "Audit Report", "Balance Sheet", "Invoice"]
        for t in types:
            if t.lower().replace(" ", "") in lower_name.replace(" ", "") or t.split()[0].lower() in lower_name:
                doc_type = t
                break
        if "itr" in lower_name: doc_type = "Income Tax Return"
        if "gst" in lower_name: doc_type = "GST Return"

        # 3. Guess FY
        fy = "2025-26"
        if "24-25" in lower_name or "2024" in lower_name: fy = "2024-25"
        elif "23-24" in lower_name or "2023" in lower_name: fy = "2023-24"
        
        # 4. Validation & Duplicates
        status = 'Matched'
        error = None
        color = 'green'
        
        if not matched_client:
            status = 'Unmatched'
            color = 'red'
            error = 'No client matched'
        elif size > 25 * 1024 * 1024:
            status = 'Error'
            color = 'red'
            error = 'File exceeds 25MB'
        elif not lower_name.endswith('.pdf'):
            status = 'Error'
            color = 'red'
            error = 'Not a PDF file'
        elif file_hash in existing_hashes or lower_name in existing_filenames:
            status = 'Duplicate'
            color = 'yellow'
            
        results.append({
            'filename': filename,
            'size': size,
            'hash': file_hash,
            'status': status,
            'color': color,
            'error': error,
            'client_id': matched_client.id if matched_client else '',
            'client_name': matched_client.display_name if matched_client else '',
            'client_code': matched_client.client_code if matched_client else '',
            'upload_id': matched_client.upload_id if matched_client else '',
            'doc_type': doc_type,
            'fy': fy,
            'duplicate_action': 'skip' if status == 'Duplicate' else ''
        })

    return jsonify({'results': results})

@api_bp.route('/bulk-upload/process', methods=['POST'])
@admin_or_employee_required
def process_bulk_upload():
    """
    Processes a single file upload from the bulk uploader.
    Creates Document or Approval Request.
    """
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400
        
    client_id = request.form.get('client_id', type=int)
    doc_type = request.form.get('doc_type', 'Other')
    fy = request.form.get('fy', '2025-26')
    duplicate_action = request.form.get('duplicate_action')
    file_hash = request.form.get('hash')
    session_id = request.form.get('session_id', type=int)
    
    if not client_id:
        return jsonify({'error': 'Client ID missing'}), 400
        
    client = ClientProfile.query.get(client_id)
    if not client:
        return jsonify({'error': 'Invalid Client'}), 400
        
    upload_session = UploadSession.query.get(session_id) if session_id else None

    # Check duplicate action
    existing_doc = None
    if file_hash:
        existing_doc = Document.query.filter_by(client_id=client_id, file_hash=file_hash, status='Active').first()
    if not existing_doc:
        existing_doc = Document.query.filter_by(client_id=client_id, original_filename=file.filename, status='Active').first()
        
    if existing_doc and duplicate_action == 'skip':
        return jsonify({'status': 'skipped', 'message': 'Skipped duplicate'})

    try:
        # Upload to Cloudinary
        res = upload_pdf(file)
        
        is_admin = current_user.role == 'admin'
        
        if not is_admin and existing_doc and duplicate_action == 'replace':
            # Employee replacing creates approval request
            doc = Document(
                client_id=client_id,
                title=file.filename.replace('.pdf', ''),
                document_type=doc_type,
                financial_year=fy,
                cloudinary_public_id=res['cloudinary_public_id'],
                cloudinary_url=res['cloudinary_url'],
                original_filename=res['original_filename'],
                file_size=res['file_size'],
                file_hash=file_hash,
                uploaded_by_id=current_user.id,
                approved=False,
                status='Pending Replace'
            )
            db.session.add(doc)
            db.session.flush()
            
            req = ApprovalRequest(
                document_id=doc.id,
                requested_by_id=current_user.id,
                request_type='Replace',
                original_document_id=existing_doc.id
            )
            db.session.add(req)
            db.session.commit()
            
            if upload_session:
                upload_session.approval_requests_created += 1
                sf = UploadSessionFile(session_id=upload_session.id, filename=file.filename, status='Pending Approval', client_id=client.id, approval_request_id=req.id)
                db.session.add(sf)
                db.session.commit()
                
            return jsonify({'status': 'pending_approval', 'message': 'Replacement requires approval'})
            
        elif not is_admin:
            # Employee upload new creates approval request
            doc = Document(
                client_id=client_id,
                title=file.filename.replace('.pdf', ''),
                document_type=doc_type,
                financial_year=fy,
                cloudinary_public_id=res['cloudinary_public_id'],
                cloudinary_url=res['cloudinary_url'],
                original_filename=res['original_filename'],
                file_size=res['file_size'],
                file_hash=file_hash,
                uploaded_by_id=current_user.id,
                approved=False,
                status='Pending'
            )
            db.session.add(doc)
            db.session.flush()
            
            req = ApprovalRequest(
                document_id=doc.id,
                requested_by_id=current_user.id,
                request_type='Upload'
            )
            db.session.add(req)
            db.session.commit()
            
            if upload_session:
                upload_session.approval_requests_created += 1
                sf = UploadSessionFile(session_id=upload_session.id, filename=file.filename, status='Pending Approval', client_id=client.id, approval_request_id=req.id)
                db.session.add(sf)
                db.session.commit()
                
            return jsonify({'status': 'pending_approval', 'message': 'Upload requires approval'})
            
        else:
            # Admin upload or replace
            if existing_doc and duplicate_action == 'replace':
                existing_doc.status = 'Archived'
                
            doc = Document(
                client_id=client_id,
                title=file.filename.replace('.pdf', ''),
                document_type=doc_type,
                financial_year=fy,
                cloudinary_public_id=res['cloudinary_public_id'],
                cloudinary_url=res['cloudinary_url'],
                original_filename=res['original_filename'],
                file_size=res['file_size'],
                file_hash=file_hash,
                uploaded_by_id=current_user.id,
                approved_by_id=current_user.id,
                approved=True,
                status='Active'
            )
            db.session.add(doc)
            db.session.commit()
            
            if upload_session:
                upload_session.successful_uploads += 1
                sf = UploadSessionFile(session_id=upload_session.id, filename=file.filename, status='Success', client_id=client.id, document_id=doc.id)
                db.session.add(sf)
                db.session.commit()
                
            return jsonify({'status': 'success', 'message': 'Uploaded successfully'})

    except Exception as e:
        if upload_session:
            upload_session.failed_uploads += 1
            sf = UploadSessionFile(session_id=upload_session.id, filename=file.filename, status='Failed', error_message=str(e), client_id=client_id)
            db.session.add(sf)
            db.session.commit()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/bulk-upload/session', methods=['POST'])
@admin_or_employee_required
def create_bulk_session():
    """Create a new tracking session before starting uploads."""
    data = request.get_json()
    total_files = data.get('total_files', 0)
    
    session = UploadSession(
        user_id=current_user.id,
        role=current_user.role,
        total_files=total_files
    )
    db.session.add(session)
    db.session.commit()
    
    return jsonify({'session_id': session.id})

@api_bp.route('/bulk-upload/session/<int:id>/complete', methods=['POST'])
@admin_or_employee_required
def complete_bulk_session(id):
    """Mark session as complete and save time taken."""
    session = UploadSession.query.get_or_404(id)
    if session.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    session.time_taken_seconds = data.get('time_taken', 0.0)
    db.session.commit()
    
    return jsonify({'status': 'success'})
