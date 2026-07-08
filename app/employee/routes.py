"""
CA Manage — Employee Management & Workspace Routes

Enables employees to view assigned clients, browse active client contact cards,
view client details, and manage document uploads through the approval request workflow.
"""
import json
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user
from ..auth.decorators import employee_required
from ..admin.forms import DocumentUploadForm, DocumentEditForm, DocumentReplaceForm
from ..utils.cloudinary_helper import upload_pdf
from ..models.client import ClientProfile
from ..models.document import Document
from ..models.approval import ApprovalRequest
from ..models.upload_session import UploadSession
from ..models.attendance import Attendance
from ..extensions import db
from ..utils.timeline import create_timeline_event
from ..utils.notification import notify_admins
from werkzeug.security import generate_password_hash
from . import employee_bp


@employee_bp.route('/dashboard')
@employee_required
def dashboard():
    """Employee dashboard with work overview."""
    assigned_count = ClientProfile.query.filter_by(
        assigned_employee_id=current_user.id,
        status='Active'
    ).count()

    # Count pending requests sent by this employee
    pending_count = ApprovalRequest.query.filter_by(
        employee_id=current_user.id,
        status='Pending'
    ).count()

    from datetime import datetime, timezone
    from ..models.employee import Employee
    today = datetime.now(timezone.utc).date()
    
    emp = Employee.query.filter_by(user_id=current_user.id).first()
    attendance_record = None
    if emp:
        attendance_record = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    
    if attendance_record:
        if attendance_record.punch_out_time:
            att_status = 'Punched Out'
        elif attendance_record.punch_in_time:
            att_status = 'Punched In'
        else:
            att_status = 'Not Punched In'
    else:
        att_status = 'Not Punched In'

    stats = {
        'assigned_clients': assigned_count,
        'pending_uploads': pending_count,
        'attendance_status': att_status,
    }

    # Get assigned client list (first 5)
    assigned_clients = ClientProfile.query.filter_by(
        assigned_employee_id=current_user.id,
        status='Active'
    ).limit(5).all()

    # Get recent upload approvals/requests
    recent_requests = ApprovalRequest.query.filter_by(
        employee_id=current_user.id
    ).order_by(ApprovalRequest.created_at.desc()).limit(5).all()

    recent_upload_sessions = UploadSession.query.filter_by(
        user_id=current_user.id
    ).order_by(UploadSession.created_at.desc()).limit(5).all()

    return render_template(
        'employee/dashboard.html',
        stats=stats,
        assigned_clients=assigned_clients,
        recent_requests=recent_requests,
        recent_upload_sessions=recent_upload_sessions,
        attendance_record=attendance_record
    )


# ── Client Listing ───────────────────────────────────────────────────
@employee_bp.route('/clients')
@employee_required
def clients_list():
    """Searchable, paginated list of clients for employee overview."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = ClientProfile.query.filter_by(status='Active')

    if search:
        query = query.filter(
            db.or_(
                ClientProfile.full_name.ilike(f'%{search}%'),
                ClientProfile.email.ilike(f'%{search}%'),
                ClientProfile.phone.ilike(f'%{search}%'),
                ClientProfile.client_code.ilike(f'%{search}%'),
                ClientProfile.PAN.ilike(f'%{search}%'),
                ClientProfile.GST.ilike(f'%{search}%'),
                ClientProfile.upload_id.ilike(f'%{search}%')
            )
        )

    pagination = query.order_by(ClientProfile.client_code.asc()).paginate(
        page=page, per_page=10, error_out=False
    )
    clients = pagination.items

    return render_template(
        'employee/clients/list.html',
        clients=clients,
        pagination=pagination,
        search=search
    )


@employee_bp.route('/clients/<int:id>')
@employee_required
def view_client(id):
    """View client profile details and documents list."""
    client = ClientProfile.query.get_or_404(id)
    if client.status != 'Active':
        flash('This client account is inactive.', 'warning')
        return redirect(url_for('employee.clients_list'))

    # Load client's active approved documents
    documents = Document.query.filter_by(
        client_id=client.id,
        approved=True,
        status='Active'
    ).all()
        
    return render_template('employee/clients/view.html', client=client, documents=documents)


# ── Document Access ──────────────────────────────────────────────────
@employee_bp.route('/documents/<int:id>/download')
@employee_required
def download_document(id):
    """Proxied download route for employees."""
    doc = Document.query.get_or_404(id)
    if doc.password_protected:
        unlocked = session.get('unlocked_documents', [])
        if doc.id not in unlocked:
            return redirect(url_for('employee.password_change_request', id=doc.id))

    url = doc.cloudinary_url
    url = url.replace('/upload/', '/upload/fl_attachment/')
    return redirect(url)

@employee_bp.route('/documents/<int:id>/preview')
@employee_required
def preview_document(id):
    """Proxied inline preview route for employees."""
    doc = Document.query.get_or_404(id)
    if doc.password_protected:
        unlocked = session.get('unlocked_documents', [])
        if doc.id not in unlocked:
            return redirect(url_for('employee.password_change_request', id=doc.id))

    url = doc.cloudinary_url
    return redirect(url)


# ── Document Management (Workflow Requests) ──────────────────────────
@employee_bp.route('/documents')
@employee_required
def documents_list():
    """Searchable, paginated directory of approved documents for all clients."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    doc_type = request.args.get('type', '').strip()
    financial_year = request.args.get('year', '').strip()

    query = Document.query.filter_by(approved=True, status='Active')

    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if financial_year:
        query = query.filter(Document.financial_year == financial_year)
    if search:
        query = query.join(ClientProfile).filter(
            db.or_(
                Document.title.ilike(f'%{search}%'),
                Document.tags.ilike(f'%{search}%'),
                Document.document_type.ilike(f'%{search}%'),
                ClientProfile.full_name.ilike(f'%{search}%'),
                ClientProfile.client_code.ilike(f'%{search}%')
            )
        )

    pagination = query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    documents = pagination.items

    doc_types = Document.sensible_defaults
    financial_years = ['2023-24', '2024-25', '2025-26', '2026-27']

    return render_template(
        'employee/documents/list.html',
        documents=documents,
        pagination=pagination,
        search=search,
        selected_type=doc_type,
        selected_year=financial_year,
        doc_types=doc_types,
        financial_years=financial_years
    )


@employee_bp.route('/documents/new', methods=['GET', 'POST'])
@employee_required
def upload_document():
    """Form to submit a new document upload request."""
    form = DocumentUploadForm()
    
    # Load clients dynamically
    clients = ClientProfile.query.filter_by(status='Active').all()
    client_choices = [(c.id, f"{c.full_name} ({c.client_code})") for c in clients]
    
    # We inject client selection dynamically
    # For WTForms we can dynamically set form fields, but it is easier to add Client Select dynamically or parse it
    selected_client_id = request.args.get('client_id', type=int)

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        client = ClientProfile.query.get_or_404(client_id)
        
        # Verify file is uploaded
        if not form.cloudinary_url.data or not form.cloudinary_public_id.data:
            flash('Please select a valid PDF file.', 'danger')
            return render_template('employee/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)
            
        try:
            # Check for duplicate hashes in existing approved documents
            existing = Document.query.filter_by(cloudinary_public_id=form.cloudinary_public_id.data, status='Active').first()
            if existing:
                flash('This file has already been uploaded in the system.', 'warning')
                return render_template('employee/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)

            # Create document draft (approved=False)
            doc = Document(
                client_id=client.id,
                title=form.title.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                tags=form.tags.data.strip() if form.tags.data else None,
                document_type=form.document_type.data,
                financial_year=form.financial_year.data,
                cloudinary_public_id=form.cloudinary_public_id.data,
                cloudinary_url=form.cloudinary_url.data,
                original_filename=form.original_filename.data,
                file_size=int(form.file_size.data),
                file_hash=None,
                upload_version=1,
                uploaded_by_id=current_user.id,
                approved=False,
                status='Active'
            )
            
            if form.password_protected.data and form.pdf_password.data:
                doc.password_protected = True
                doc.pdf_password = generate_password_hash(form.pdf_password.data)
                
            db.session.add(doc)
            db.session.flush()

            # Create approval request
            req = ApprovalRequest(
                employee_id=current_user.id,
                document_id=doc.id,
                request_type='Upload',
                proposed_values=json.dumps({
                    'title': doc.title,
                    'tags': doc.tags,
                    'document_type': doc.document_type,
                    'financial_year': doc.financial_year,
                    'password_protected': doc.password_protected
                }),
                status='Pending'
            )
            db.session.add(req)
            db.session.commit()
            
            create_timeline_event(
                client_id=doc.client_id,
                event_type='Approval Request Created',
                description=f'New Upload request for "{doc.title}".',
                user_id=current_user.id,
                document_id=doc.id
            )
            db.session.commit()
            
            notify_admins(f"New Document Upload Request for '{doc.title}' by {current_user.full_name}", link=url_for('admin.approvals_list'), title='New Upload Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)

            flash(f"Upload request for '{doc.title}' submitted to administrators for approval.", 'success')
            return redirect(url_for('employee.requests_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Upload failed: {str(e)}", 'danger')

    return render_template('employee/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)

@employee_bp.route('/documents/bulk-upload')
@employee_required
def bulk_upload():
    """Single page app for bulk uploading and mapping PDFs as an employee."""
    # Employees can only upload to assigned clients
    assigned_clients = current_user.assigned_clients
    client_choices = [{'id': c.id, 'name': f"{c.full_name} ({c.client_code})"} for c in assigned_clients if c.status == 'Active']
    doc_types = Document.sensible_defaults
    return render_template('employee/documents/bulk_upload.html', clients=client_choices, doc_types=doc_types)

@employee_bp.route('/documents/<int:id>/replace', methods=['GET', 'POST'])
@employee_required
def replace_document(id):
    """Request replacement of a production PDF."""
    doc = Document.query.get_or_404(id)
    form = DocumentReplaceForm()

    if form.validate_on_submit():
        if not form.cloudinary_url.data or not form.cloudinary_public_id.data:
            flash('Please upload a replacement file first.', 'danger')
            return render_template('employee/documents/replace.html', form=form, document=doc)
            
        try:
            # Check duplicates
            existing = Document.query.filter_by(cloudinary_public_id=form.cloudinary_public_id.data, status='Active').first()
            if existing:
                flash('This file matches an existing document.', 'warning')
                return render_template('employee/documents/replace.html', form=form, document=doc)

            # Create pending Replace request
            req = ApprovalRequest(
                employee_id=current_user.id,
                document_id=doc.id,
                request_type='Replace',
                previous_values=json.dumps({
                    'cloudinary_public_id': doc.cloudinary_public_id,
                    'cloudinary_url': doc.cloudinary_url,
                    'original_filename': doc.original_filename,
                    'file_size': doc.file_size,
                    'file_hash': doc.file_hash
                }),
                proposed_values=json.dumps({
                    'cloudinary_public_id': form.cloudinary_public_id.data,
                    'cloudinary_url': form.cloudinary_url.data,
                    'original_filename': form.original_filename.data,
                    'file_size': int(form.file_size.data),
                    'file_hash': None
                }),
                status='Pending'
            )
            db.session.add(req)
            db.session.commit()
            
            create_timeline_event(
                client_id=doc.client_id,
                event_type='Approval Request Created',
                description=f'Replacement requested for "{doc.title}".',
                user_id=current_user.id,
                document_id=doc.id
            )
            db.session.commit()
            
            notify_admins(f"Document Replacement Request for '{doc.title}' by {current_user.full_name}", link=url_for('admin.approvals_list'), title='Replacement Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)

            flash(f"Replacement request for '{doc.title}' submitted for admin approval.", 'success')
            return redirect(url_for('employee.requests_list'))

        except Exception as e:
            flash(f"Replacement request failed: {str(e)}", 'danger')

    return render_template('employee/documents/replace.html', form=form, document=doc)


@employee_bp.route('/documents/<int:id>/edit', methods=['GET', 'POST'])
@employee_required
def edit_document(id):
    """Request changes to document metadata."""
    doc = Document.query.get_or_404(id)
    form = DocumentEditForm(obj=doc)

    if form.validate_on_submit():
        # Create metadata edit request
        req = ApprovalRequest(
            employee_id=current_user.id,
            document_id=doc.id,
            request_type='Metadata Edit',
            previous_values=json.dumps({
                'title': doc.title,
                'description': doc.description,
                'tags': doc.tags,
                'document_type': doc.document_type,
                'financial_year': doc.financial_year
            }),
            proposed_values=json.dumps({
                'title': form.title.data.strip(),
                'description': form.description.data.strip() if form.description.data else None,
                'tags': form.tags.data.strip() if form.tags.data else None,
                'document_type': form.document_type.data,
                'financial_year': form.financial_year.data
            }),
            status='Pending'
        )
        db.session.add(req)
        db.session.commit()
        
        create_timeline_event(
            client_id=doc.client_id,
            event_type='Approval Request Created',
            description=f'Metadata edit requested for "{doc.title}".',
            user_id=current_user.id,
            document_id=doc.id
        )
        db.session.commit()
        
        notify_admins(f"Metadata Edit Request for '{doc.title}' by {current_user.full_name}", link=url_for('admin.approvals_list'), title='Edit Request', category='approvals', priority='normal', entity_type='Document', entity_id=doc.id)

        flash(f"Metadata edit request for '{doc.title}' submitted for approval.", 'success')
        return redirect(url_for('employee.requests_list'))

    return render_template('employee/documents/edit.html', form=form, document=doc)


@employee_bp.route('/documents/<int:id>/delete-request', methods=['POST'])
@employee_required
def delete_document_request(id):
    """Request soft deletion of a document."""
    doc = Document.query.get_or_404(id)
    
    req = ApprovalRequest(
        employee_id=current_user.id,
        document_id=doc.id,
        request_type='Delete',
        status='Pending'
    )
    db.session.add(req)
    db.session.commit()
    
    create_timeline_event(
        client_id=doc.client_id,
        event_type='Approval Request Created',
        description=f'Deletion requested for "{doc.title}".',
        user_id=current_user.id,
        document_id=doc.id
    )
    db.session.commit()
    
    notify_admins(f"Delete Document Request for '{doc.title}' by {current_user.full_name}", link=url_for('admin.approvals_list'), title='Delete Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)
    
    flash(f"Delete request for '{doc.title}' submitted.", 'success')
    return redirect(url_for('employee.requests_list'))


@employee_bp.route('/documents/<int:id>/password-request', methods=['GET', 'POST'])
@employee_required
def password_change_request(id):
    """Request change or addition of access password."""
    doc = Document.query.get_or_404(id)
    
    # We reuse DocumentEditForm's password fields
    form = DocumentEditForm(obj=doc)
    
    if request.method == 'POST':
        pw_protected = form.password_protected.data
        pw = form.pdf_password.data
        
        proposed = {'password_protected': pw_protected}
        if pw_protected and pw:
            proposed['pdf_password'] = generate_password_hash(pw)
        elif not pw_protected:
            proposed['pdf_password'] = None
            
        req = ApprovalRequest(
            employee_id=current_user.id,
            document_id=doc.id,
            request_type='Password Change',
            previous_values=json.dumps({
                'password_protected': doc.password_protected
            }),
            proposed_values=json.dumps(proposed),
            status='Pending'
        )
        db.session.add(req)
        db.session.commit()
        
        create_timeline_event(
            client_id=doc.client_id,
            event_type='Approval Request Created',
            description=f'Password modification requested for "{doc.title}".',
            user_id=current_user.id,
            document_id=doc.id
        )
        db.session.commit()
        
        notify_admins(f"Password Edit Request for '{doc.title}' by {current_user.full_name}", link=url_for('admin.approvals_list'), title='Password Edit Request', category='approvals', priority='high', entity_type='Document', entity_id=doc.id)

        flash(f"Password modification request for '{doc.title}' submitted.", 'success')
        return redirect(url_for('employee.requests_list'))

    return render_template('employee/documents/password_request.html', form=form, document=doc)


@employee_bp.route('/requests')
@employee_required
def requests_list():
    """List of all approval requests sent by the employee."""
    page = request.args.get('page', 1, type=int)
    query = ApprovalRequest.query.filter_by(employee_id=current_user.id)
    
    pagination = query.order_by(ApprovalRequest.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    requests = pagination.items
    
    return render_template('employee/requests/list.html', requests=requests, pagination=pagination)
