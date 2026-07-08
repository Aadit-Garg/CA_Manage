"""
CA Manage — Admin Dashboard & Management Routes

Provides summary statistics and administration endpoints for managing employees, clients,
bulk Excel imports, document approvals, version history, and direct PDF upload/edit features.
"""
from datetime import datetime, timezone
import json
from flask import render_template, redirect, url_for, flash, request, current_app, send_file, session
from flask_login import current_user
from ..auth.decorators import admin_required
from ..extensions import db
from ..models.user import User
from ..models.client import ClientProfile
from ..models.employee import Employee
from ..models.document import Document
from ..models.document_version import DocumentVersion
from ..models.approval import ApprovalRequest
from ..models.upload_session import UploadSession
from ..utils.logging import get_logger, log_user_action
from ..utils.cloudinary_helper import upload_pdf, delete_pdf
from ..utils.import_helper import generate_excel_template, parse_and_validate_excel
from ..utils.timeline import create_timeline_event
from ..utils.notification import create_notification
from .forms import EmployeeForm, ClientForm, AdminResetPasswordForm, DocumentUploadForm, DocumentEditForm, DocumentReplaceForm, BulkUploadForm
from . import admin_bp

logger = get_logger(__name__)


# ── Dashboard ───────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with system overview statistics."""
    stats = {
        'total_clients': ClientProfile.query.count(),
        'active_clients': ClientProfile.query.filter_by(status='Active').count(),
        'total_employees': Employee.query.count(),
        'active_employees': Employee.query.filter_by(status='Active').count(),
        'total_documents': Document.query.filter_by(status='Active').count(),
        'pending_approvals': ApprovalRequest.query.filter_by(status='Pending').count(),
        'recent_documents': Document.query.filter_by(status='Active').order_by(Document.created_at.desc()).limit(5).all(),
    }

    # Activity Feed (Recent Audit Logs)
    from ..models.audit import AuditLog
    recent_activity = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    
    # Recent requests and upload sessions
    recent_requests = ApprovalRequest.query.order_by(ApprovalRequest.created_at.desc()).limit(5).all()
    recent_upload_sessions = UploadSession.query.order_by(UploadSession.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_requests=recent_requests,
        recent_upload_sessions=recent_upload_sessions,
        recent_activity=recent_activity
    )


# ── System Admin Management ───────────────────────────────────────────
@admin_bp.route('/system-admins')
@admin_required
def system_admins_list():
    """List of all system administrators."""
    admins = User.query.filter_by(role=User.ROLE_ADMIN).order_by(User.created_at.desc()).all()
    return render_template('admin/system_admins/list.html', admins=admins)


@admin_bp.route('/system-admins/new', methods=['GET', 'POST'])
@admin_required
def create_system_admin():
    """Create a new system administrator."""
    from .forms import SystemAdminForm
    form = SystemAdminForm()
    
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower().strip(),
            full_name=form.full_name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=User.ROLE_ADMIN,
            is_active=True
        )
        user.set_password('Admin@123')
        db.session.add(user)
        db.session.commit()

        log_user_action(logger, current_user, 'create_admin', module='admin', description=f'Created admin {user.email}')
        flash(f"System Administrator {user.full_name} created. Default password: 'Admin@123'.", 'success')
        return redirect(url_for('admin.system_admins_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/system_admins/new.html', form=form), status_code


@admin_bp.route('/system-admins/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_system_admin(id):
    """Edit existing system administrator profile."""
    admin = User.query.get_or_404(id)
    if admin.role != User.ROLE_ADMIN:
        flash("Invalid user role.", "danger")
        return redirect(url_for('admin.system_admins_list'))
        
    from .forms import SystemAdminForm
    form = SystemAdminForm(original_user_id=admin.id, obj=admin)

    if form.validate_on_submit():
        form.populate_obj(admin)
        admin.email = form.email.data.lower().strip()
        db.session.commit()

        log_user_action(logger, current_user, 'edit_admin', module='admin', entity_id=admin.id, description=f'Edited admin {admin.email}')
        flash(f"System Administrator {admin.full_name} updated successfully.", 'success')
        return redirect(url_for('admin.system_admins_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/system_admins/edit.html', form=form, admin=admin), status_code


@admin_bp.route('/system-admins/<int:id>/toggle-status', methods=['POST'])
@admin_required
def toggle_system_admin_status(id):
    """Enable or disable a system administrator login."""
    admin = User.query.get_or_404(id)
    if admin.role != User.ROLE_ADMIN:
        flash("Invalid user role.", "danger")
        return redirect(url_for('admin.system_admins_list'))
        
    if admin.id == current_user.id:
        flash("You cannot disable your own account.", "danger")
        return redirect(url_for('admin.system_admins_list'))

    if admin.is_active:
        admin.is_active = False
        action = 'disable_admin'
        msg = f"System Administrator {admin.full_name} has been disabled."
    else:
        admin.is_active = True
        action = 'enable_admin'
        msg = f"System Administrator {admin.full_name} has been enabled."
    db.session.commit()

    log_user_action(logger, current_user, action, module='admin', entity_id=admin.id, description=f'{action} on admin {admin.email}')
    flash(msg, 'success')
    return redirect(url_for('admin.system_admins_list'))


@admin_bp.route('/system-admins/<int:id>/reset-password', methods=['GET', 'POST'])
@admin_required
def reset_system_admin_password(id):
    """Reset password of a system administrator."""
    admin = User.query.get_or_404(id)
    if admin.role != User.ROLE_ADMIN:
        flash("Invalid user role.", "danger")
        return redirect(url_for('admin.system_admins_list'))
        
    from .forms import AdminResetPasswordForm
    form = AdminResetPasswordForm()
    
    if form.validate_on_submit():
        admin.set_password(form.password.data)
        db.session.commit()
        
        log_user_action(logger, current_user, 'reset_password_admin', module='admin', entity_id=admin.id, description=f'Password reset for admin {admin.email}')
        flash(f"Password reset successfully for {admin.full_name}.", 'success')
        return redirect(url_for('admin.system_admins_list'))
        
    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/system_admins/reset_password.html', form=form, admin=admin), status_code


@admin_bp.route('/system-admins/<int:id>/delete', methods=['POST'])
@admin_required
def delete_system_admin(id):
    """Delete a system administrator."""
    admin = User.query.get_or_404(id)
    if admin.role != User.ROLE_ADMIN:
        flash("Invalid user role.", "danger")
        return redirect(url_for('admin.system_admins_list'))
        
    if admin.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('admin.system_admins_list'))

    db.session.delete(admin)
    db.session.commit()

    log_user_action(logger, current_user, 'delete_admin', module='admin', description=f'Deleted admin {admin.email}')
    flash(f"System Administrator {admin.full_name} has been deleted.", 'success')
    return redirect(url_for('admin.system_admins_list'))


# ── Employee Management ──────────────────────────────────────────────
@admin_bp.route('/employees')
@admin_required
def employees_list():
    """Paginated, searchable list of employees."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Employee.query
    if search:
        query = query.filter(
            db.or_(
                Employee.full_name.ilike(f'%{search}%'),
                Employee.email.ilike(f'%{search}%'),
                Employee.phone.ilike(f'%{search}%'),
                Employee.designation.ilike(f'%{search}%')
            )
        )

    pagination = query.order_by(Employee.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    employees = pagination.items

    return render_template(
        'admin/employees/list.html',
        employees=employees,
        pagination=pagination,
        search=search
    )


@admin_bp.route('/employees/new', methods=['GET', 'POST'])
@admin_required
def create_employee():
    """Create a new employee profile and credentials."""
    form = EmployeeForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower().strip(),
            full_name=form.full_name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=User.ROLE_EMPLOYEE,
            is_active=True
        )
        
        # Use provided password or default
        password = form.password.data if form.password.data else 'Employee@123'
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()

        employee = Employee(
            user_id=user.id,
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            designation=form.designation.data.strip() if form.designation.data else None,
            joining_date=form.joining_date.data,
            notes=form.notes.data.strip() if form.notes.data else None,
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

        log_user_action(logger, current_user, 'create_employee', module='employees', entity_type='Employee', entity_id=employee.id, description=f'Created employee {employee.email}')
        flash(f"Employee {employee.full_name} created. Default password: 'Employee@123'.", 'success')
        return redirect(url_for('admin.employees_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/employees/new.html', form=form), status_code


@admin_bp.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_employee(id):
    """Edit existing employee profile."""
    employee = Employee.query.get_or_404(id)
    form = EmployeeForm(original_user_id=employee.user_id, obj=employee)

    if form.validate_on_submit():
        form.populate_obj(employee)
        user = employee.user
        user.email = employee.email
        user.full_name = employee.full_name
        user.phone = employee.phone
        
        if form.password.data:
            user.set_password(form.password.data)
            
        db.session.commit()

        log_user_action(logger, current_user, 'edit_employee', module='employees', entity_type='Employee', entity_id=employee.id, description=f'Edited employee {employee.email}')
        flash(f"Employee {employee.full_name} updated successfully.", 'success')
        return redirect(url_for('admin.employees_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/employees/edit.html', form=form, employee=employee), status_code


@admin_bp.route('/employees/<int:id>/toggle-status', methods=['POST'])
@admin_required
def toggle_employee_status(id):
    """Enable or disable an employee login and profile status."""
    employee = Employee.query.get_or_404(id)
    user = employee.user
    if user.is_active:
        user.is_active = False
        employee.status = 'Inactive'
        action = 'disable_employee'
        msg = f"Employee {employee.full_name} has been disabled."
    else:
        user.is_active = True
        employee.status = 'Active'
        action = 'enable_employee'
        msg = f"Employee {employee.full_name} has been enabled."
    db.session.commit()

    log_user_action(logger, current_user, action, module='employees', entity_type='Employee', entity_id=employee.id, description=f'{action} on employee {employee.email}')
    flash(msg, 'success')
    return redirect(url_for('admin.employees_list'))


@admin_bp.route('/employees/<int:id>/reset-password', methods=['GET', 'POST'])
@admin_required
def reset_employee_password(id):
    """Reset password of an employee."""
    employee = Employee.query.get_or_404(id)
    form = AdminResetPasswordForm()
    if form.validate_on_submit():
        employee.user.set_password(form.password.data)
        db.session.commit()

        log_user_action(logger, current_user, 'reset_employee_password', module='employees', entity_type='Employee', entity_id=employee.id, description=f'Reset password for employee {employee.email}')
        flash(f"Password reset successful for {employee.full_name}.", 'success')
        return redirect(url_for('admin.employees_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/employees/reset_password.html', form=form, employee=employee), status_code


@admin_bp.route('/employees/<int:id>/delete', methods=['POST'])
@admin_required
def delete_employee(id):
    """Delete an employee and their profile."""
    employee = Employee.query.get_or_404(id)
    user = employee.user
    
    db.session.delete(user)
    db.session.commit()

    log_user_action(logger, current_user, 'delete_employee', module='employees', description=f'Deleted employee {employee.email}')
    flash(f"Employee {employee.full_name} has been deleted.", 'success')
    return redirect(url_for('admin.employees_list'))


@admin_bp.route('/employees/<int:id>')
@admin_required
def view_employee(id):
    employee = Employee.query.get_or_404(id)
    return render_template('admin/employees/view.html', employee=employee)


# ── Client Management ────────────────────────────────────────────────
@admin_bp.route('/clients')
@admin_required
def clients_list():
    """Paginated, searchable list of clients."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')

    # Specify the foreign key to avoid AmbiguousForeignKeysError
    query = ClientProfile.query.join(User, ClientProfile.user_id == User.id)
    if status_filter == 'Enabled':
        query = query.filter(User.is_active == True)
    elif status_filter == 'Disabled':
        query = query.filter(User.is_active == False)

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
        'admin/clients/list.html',
        clients=clients,
        pagination=pagination,
        search=search,
        status_filter=status_filter
    )


@admin_bp.route('/clients/new', methods=['GET', 'POST'])
@admin_required
def create_client():
    """Create a new client profile and login account."""
    form = ClientForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower().strip(),
            full_name=form.full_name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=User.ROLE_CLIENT,
            is_active=True
        )
        
        password = form.password.data if form.password.data else 'Client@123'
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()

        profile = ClientProfile(
            user_id=user.id,
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            firm_name=form.firm_name.data.strip() if form.firm_name.data else None,
            client_type=form.client_type.data,
            PAN=form.PAN.data.upper().strip() if form.PAN.data else None,
            GST=form.GST.data.upper().strip() if form.GST.data else None,
            address=form.address.data.strip() if form.address.data else None,
            city=form.city.data.strip() if form.city.data else None,
            state=form.state.data.strip() if form.state.data else None,
            pincode=form.pincode.data.strip() if form.pincode.data else None,
            notes=form.notes.data.strip() if form.notes.data else None,
            assigned_employee_id=form.assigned_employee_id.data if form.assigned_employee_id.data > 0 else None,
            status='Active'
        )
        db.session.add(profile)
        db.session.commit()
        
        create_timeline_event(
            client_id=profile.id,
            event_type='Client Created',
            description=f'Client profile created by {current_user.full_name}.',
            user_id=current_user.id
        )
        db.session.commit()

        log_user_action(logger, current_user, 'create_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Created client {profile.email}')
        pwd_msg = "Custom password set." if form.password.data else "Default password: 'Client@123'."
        flash(f"Client {profile.full_name} created. {pwd_msg}", 'success')
        return redirect(url_for('admin.clients_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/clients/new.html', form=form), status_code


@admin_bp.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_client(id):
    profile = ClientProfile.query.get_or_404(id)
    form = ClientForm(original_user_id=profile.user_id, obj=profile)

    if request.method == 'GET':
        form.assigned_employee_id.data = profile.assigned_employee_id or 0

    if form.validate_on_submit():
        form.populate_obj(profile)
        profile.assigned_employee_id = None if form.assigned_employee_id.data == 0 else form.assigned_employee_id.data
        user = profile.user
        user.email = profile.email
        user.full_name = profile.full_name
        user.phone = profile.phone
        
        if form.password.data:
            user.set_password(form.password.data)
            
        db.session.commit()
        
        create_timeline_event(
            client_id=profile.id,
            event_type='Client Updated',
            description=f'Client profile updated by {current_user.full_name}.',
            user_id=current_user.id
        )
        db.session.commit()

        log_user_action(logger, current_user, 'edit_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Edited client {profile.email}')
        flash(f"Client {profile.full_name} updated successfully.", 'success')
        return redirect(url_for('admin.clients_list'))

    status_code = 422 if request.method == 'POST' else 200
    return render_template('admin/clients/edit.html', form=form, client=profile), status_code


@admin_bp.route('/clients/<int:id>/toggle-status', methods=['POST'])
@admin_required
def toggle_client_status(id):
    profile = ClientProfile.query.get_or_404(id)
    user = profile.user
    if user.is_active:
        user.is_active = False
        action = 'disable_client'
        msg = f"Client account for {profile.full_name} disabled."
    else:
        user.is_active = True
        action = 'enable_client'
        msg = f"Client account for {profile.full_name} enabled."
    db.session.commit()
    
    create_timeline_event(
        client_id=profile.id,
        event_type='Client Disabled' if not user.is_active else 'Client Restored',
        description=msg,
        user_id=current_user.id
    )
    db.session.commit()

    log_user_action(logger, current_user, action, module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'{action} on client {profile.email}')
    flash(msg, 'success')
    return redirect(url_for('admin.clients_list'))


@admin_bp.route('/clients/<int:id>/delete', methods=['POST'])
@admin_required
def delete_client(id):
    profile = ClientProfile.query.get_or_404(id)
    profile.status = 'Inactive'
    profile.user.is_active = False
    db.session.commit()
    
    create_timeline_event(
        client_id=profile.id,
        event_type='Client Disabled',
        description=f"Client account for {profile.full_name} marked as inactive.",
        user_id=current_user.id
    )
    db.session.commit()

    log_user_action(logger, current_user, 'disable_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Disabled client {profile.email}')
    flash(f"Client {profile.full_name} soft-deleted.", 'success')
    return redirect(url_for('admin.clients_list'))


@admin_bp.route('/clients/<int:id>/restore', methods=['POST'])
@admin_required
def restore_client(id):
    profile = ClientProfile.query.get_or_404(id)
    profile.status = 'Active'
    profile.user.is_active = True
    db.session.commit()

    log_user_action(logger, current_user, 'restore_client', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Restored client {profile.email}')
    flash(f"Client {profile.full_name} restored.", 'success')
    return redirect(url_for('admin.clients_list', status='Inactive'))


@admin_bp.route('/clients/<int:id>/reset-password', methods=['GET', 'POST'])
@admin_required
def reset_client_password(id):
    profile = ClientProfile.query.get_or_404(id)
    form = AdminResetPasswordForm()
    if form.validate_on_submit():
        profile.user.set_password(form.password.data)
        db.session.commit()

        log_user_action(logger, current_user, 'reset_client_password', module='clients', entity_type='ClientProfile', entity_id=profile.id, description=f'Reset password for client {profile.email}')
        flash(f"Password reset successful for {profile.full_name}.", 'success')
        return redirect(url_for('admin.clients_list'))

    return render_template('admin/clients/reset_password.html', form=form, client=profile)


@admin_bp.route('/clients/<int:id>')
@admin_required
def view_client(id):
    profile = ClientProfile.query.get_or_404(id)
    # Load client's active approved documents
    documents = Document.query.filter_by(
        client_id=profile.id,
        approved=True,
        status='Active'
    ).all()
    return render_template('admin/clients/view.html', client=profile, documents=documents)


# ── Bulk Excel Client Import ─────────────────────────────────────────
@admin_bp.route('/clients/import-template')
@admin_required
def download_import_template():
    """Download the client import Excel template with layout formatting."""
    stream = generate_excel_template()
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="CA_Manage_Clients_Template.xlsx"
    )


@admin_bp.route('/clients/import', methods=['GET', 'POST'])
@admin_required
def import_clients():
    """Bulk Excel client upload and validation routing."""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Please upload a valid Excel spreadsheet.', 'danger')
            return redirect(url_for('admin.import_clients'))
            
        try:
            valid_rows, invalid_rows = parse_and_validate_excel(file.stream)
            
            # Save valid entries temporarily in session to allow committing
            session['pending_import_rows'] = valid_rows
            
            return render_template('admin/clients/import_preview.html', 
                                   valid_rows=valid_rows, 
                                   invalid_rows=invalid_rows)
        except Exception as e:
            current_app.logger.error(f"Failed to parse template: {str(e)}", exc_info=True)
            flash(f"Failed to parse template: {str(e)}", 'danger')
            return redirect(url_for('admin.import_clients'))
            
    return render_template('admin/clients/import.html')


@admin_bp.route('/clients/import/commit', methods=['POST'])
@admin_required
def commit_import():
    """Commit the parsed spreadsheet rows stored in session."""
    valid_rows = session.pop('pending_import_rows', None)
    if not valid_rows:
        flash('No pending client records found. Please upload again.', 'warning')
        return redirect(url_for('admin.import_clients'))
        
    success_count = 0
    duplicate_count = 0
    
    for row in valid_rows:
        # Prevent race condition duplicates
        existing = User.query.filter_by(email=row['email']).first()
        if existing:
            duplicate_count += 1
            continue
            
        user = User(
            email=row['email'],
            full_name=row['full_name'],
            phone=row['phone'],
            role=User.ROLE_CLIENT,
            is_active=True
        )
        user.set_password('Client@123')
        db.session.add(user)
        db.session.flush()
        
        profile = ClientProfile(
            user_id=user.id,
            full_name=row['full_name'],
            email=row['email'],
            phone=row['phone'],
            address=row['address'],
            city=row['city'],
            state=row['state'],
            pincode=row['pincode'],
            PAN=row['PAN'],
            GST=row['GST'],
            notes=row['notes'],
            status='Active'
        )
        db.session.add(profile)
        success_count += 1
        
    db.session.commit()
    log_user_action(logger, current_user, 'bulk_import_clients', module='clients', description=f'Bulk imported {success_count} clients')
    
    flash(f"Import complete: {success_count} clients successfully imported. {duplicate_count} skipped as duplicates.", 'success')
    return redirect(url_for('admin.clients_list'))


# ── Document Direct Control ──────────────────────────────────────────
@admin_bp.route('/documents')
@admin_required
def documents_list():
    """Paginated, searchable document library for admins."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    doc_type = request.args.get('type', '').strip()
    financial_year = request.args.get('year', '').strip()

    query = Document.query.filter_by(status='Active')

    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if financial_year:
        query = query.filter(Document.financial_year == financial_year)
    if search:
        query = query.join(ClientProfile).filter(
            db.or_(
                Document.title.ilike(f'%{search}%'),
                Document.tags.ilike(f'%{search}%'),
                Document.original_filename.ilike(f'%{search}%'),
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
        'admin/documents/list.html',
        documents=documents,
        pagination=pagination,
        search=search,
        selected_type=doc_type,
        selected_year=financial_year,
        doc_types=doc_types,
        financial_years=financial_years
    )


@admin_bp.route('/documents/new', methods=['GET', 'POST'])
@admin_required
def upload_document():
    """Directly upload a PDF for a client (bypasses approval)."""
    form = DocumentUploadForm()
    
    clients = ClientProfile.query.filter_by(status='Active').all()
    client_choices = [(c.id, f"{c.full_name} ({c.client_code})") for c in clients]
    selected_client_id = request.args.get('client_id', type=int)

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        if not client_id:
            flash('Please select a client.', 'danger')
            return render_template('admin/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)
            
        client = ClientProfile.query.get_or_404(client_id)
        
        if not form.cloudinary_url.data or not form.cloudinary_public_id.data:
            flash('Please upload a valid PDF file.', 'danger')
            return render_template('admin/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)
            
        try:
            # We don't have file hash anymore since it was uploaded directly
            # We can use cloudinary_public_id for uniqueness check
            existing = Document.query.filter_by(cloudinary_public_id=form.cloudinary_public_id.data, status='Active').first()
            if existing:
                flash('This document has already been uploaded in the system.', 'warning')
                return render_template('admin/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)

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
                file_hash=None, # File hash cannot be reliably calculated from client side securely without heavy JS
                upload_version=1,
                uploaded_by_id=current_user.id,
                approved_by_id=current_user.id,
                approved=True,
                status='Active'
            )
            
            if form.password_protected.data and form.pdf_password.data:
                doc.password_protected = True
                doc.pdf_password = generate_password_hash(form.pdf_password.data)
                
            db.session.add(doc)
            db.session.commit()
            
            create_timeline_event(
                client_id=client.id,
                event_type='Document Uploaded',
                description=f'Document "{doc.title}" uploaded.',
                user_id=current_user.id,
                document_id=doc.id
            )
            db.session.commit()

            log_user_action(current_app.logger, current_user, 'create_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Uploaded document {doc.title}')
            flash(f"Document '{doc.title}' uploaded and published successfully.", 'success')
            return redirect(url_for('admin.documents_list'))
            
        except Exception as e:
            flash(f"Upload failed: {str(e)}", 'danger')

    return render_template('admin/documents/new.html', form=form, clients=client_choices, selected_client_id=selected_client_id)


@admin_bp.route('/documents/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_document(id):
    """Directly edit document metadata."""
    doc = Document.query.get_or_404(id)
    form = DocumentEditForm(obj=doc)

    if form.validate_on_submit():
        form.populate_obj(doc)
        
        # Handle password modifications
        if form.password_protected.data:
            doc.password_protected = True
            if form.pdf_password.data:
                doc.pdf_password = generate_password_hash(form.pdf_password.data)
        else:
            doc.password_protected = False
            doc.pdf_password = None
            
        db.session.commit()
        
        create_timeline_event(
            client_id=doc.client_id,
            event_type='Document Updated',
            description=f'Document metadata or settings updated.',
            user_id=current_user.id,
            document_id=doc.id
        )
        db.session.commit()
        
        log_user_action(logger, current_user, 'edit_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Edited document {doc.title}')
        
        flash('Document details updated successfully.', 'success')
        return redirect(url_for('admin.documents_list'))

    return render_template('admin/documents/edit.html', form=form, document=doc)


@admin_bp.route('/documents/<int:id>/replace', methods=['GET', 'POST'])
@admin_required
def replace_document(id):
    """Directly replace a production PDF, preserving older version in history."""
    doc = Document.query.get_or_404(id)
    form = DocumentReplaceForm()

    if form.validate_on_submit():
        if not form.cloudinary_url.data or not form.cloudinary_public_id.data:
            flash('Please upload a replacement file first.', 'danger')
            return render_template('admin/documents/replace.html', form=form, document=doc)
            
        try:
            # Duplicate check
            existing = Document.query.filter_by(cloudinary_public_id=form.cloudinary_public_id.data, status='Active').first()
            if existing:
                flash('This file matches an existing document.', 'warning')
                return render_template('admin/documents/replace.html', form=form, document=doc)

            # Archive current values
            history = DocumentVersion(
                document_id=doc.id,
                version_number=doc.upload_version,
                cloudinary_public_id=doc.cloudinary_public_id,
                cloudinary_url=doc.cloudinary_url,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                file_hash=doc.file_hash,
                uploaded_by_id=doc.uploaded_by_id
            )
            db.session.add(history)

            # Update Document with new file details
            doc.cloudinary_public_id = form.cloudinary_public_id.data
            doc.cloudinary_url = form.cloudinary_url.data
            doc.original_filename = form.original_filename.data
            doc.file_size = int(form.file_size.data)
            doc.file_hash = None
            doc.uploaded_by_id = current_user.id
            doc.upload_version += 1
            
            db.session.commit()
            
            create_timeline_event(
                client_id=doc.client_id,
                event_type='Document Replaced',
                description=f'Document replaced with v{doc.upload_version}.',
                user_id=current_user.id,
                document_id=doc.id
            )
            db.session.commit()
            
            log_user_action(logger, current_user, 'replace_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Replaced document {doc.title}')
            
            flash(f"Document replaced successfully. Now at version {doc.upload_version}.", 'success')
            return redirect(url_for('admin.documents_list'))
            
        except Exception as e:
            flash(f"Replacement failed: {str(e)}", 'danger')

    return render_template('admin/documents/replace.html', form=form, document=doc)


@admin_bp.route('/documents/<int:id>/delete', methods=['POST'])
@admin_required
def delete_document(id):
    """Soft delete a document."""
    doc = Document.query.get_or_404(id)
    doc.status = 'Deleted'
    db.session.commit()
    
    create_timeline_event(
        client_id=doc.client_id,
        event_type='Document Deleted',
        description=f'Document "{doc.title}" deleted.',
        user_id=current_user.id,
        document_id=doc.id
    )
    db.session.commit()
    
    log_user_action(logger, current_user, 'delete_document', module='documents', entity_type='Document', entity_id=doc.id, description=f'Deleted document {doc.title}')
    flash(f"Document '{doc.title}' soft-deleted.", 'success')
    return redirect(url_for('admin.documents_list'))


@admin_bp.route('/documents/<int:id>/download')
@admin_required
def download_document(id):
    """Proxied download route for admin."""
    import urllib.parse
    doc = Document.query.get_or_404(id)
    safe_filename = urllib.parse.quote(doc.original_filename)
    url = doc.cloudinary_url
    if '/raw/upload/' not in url:
        url = url.replace('/upload/', f'/upload/fl_attachment:{safe_filename}/')
    return redirect(url)


@admin_bp.route('/documents/<int:id>/preview')
@admin_required
def preview_document(id):
    """Proxied inline preview route for admin."""
    doc = Document.query.get_or_404(id)
    url = doc.cloudinary_url
    return redirect(url)



@admin_bp.route('/documents/<int:id>/history')
@admin_required
def view_document_history(id):
    """View version history of a document."""
    doc = Document.query.get_or_404(id)
    return render_template('admin/documents/history.html', document=doc)


@admin_bp.route('/documents/version/<int:v_id>/restore', methods=['POST'])
@admin_required
def restore_document_version(v_id):
    """Restore an older PDF file version from history, bumping version number."""
    ver = DocumentVersion.query.get_or_404(v_id)
    doc = ver.document
    
    # Save current document details to history before restoring
    history = DocumentVersion(
        document_id=doc.id,
        version_number=doc.upload_version,
        cloudinary_public_id=doc.cloudinary_public_id,
        cloudinary_url=doc.cloudinary_url,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        file_hash=doc.file_hash,
        uploaded_by_id=doc.uploaded_by_id
    )
    db.session.add(history)
    
    # Restore older details
    doc.cloudinary_public_id = ver.cloudinary_public_id
    doc.cloudinary_url = ver.cloudinary_url
    doc.original_filename = ver.original_filename
    doc.file_size = ver.file_size
    doc.file_hash = ver.file_hash
    doc.uploaded_by_id = ver.uploaded_by_id
    doc.upload_version += 1
    
    db.session.commit()
    log_user_action(logger, current_user, 'restore_document_version', module='documents', entity_type='Document', entity_id=doc.id, description=f'Restored document {doc.title} to version {ver.version_number}')
    
    flash(f"Restored version {ver.version_number} as version {doc.upload_version}.", 'success')
    return redirect(url_for('admin.view_document_history', id=doc.id))


# ── Bulk PDF Upload Mapping ──────────────────────────────────────────
@admin_bp.route('/documents/bulk-upload')
@admin_required
def bulk_upload():
    """Single page app for bulk uploading and mapping PDFs."""
    clients = ClientProfile.query.filter_by(status='Active').all()
    client_choices = [{'id': c.id, 'name': f"{c.full_name} ({c.client_code})"} for c in clients]
    doc_types = Document.sensible_defaults
    return render_template('admin/documents/bulk_upload.html', clients=client_choices, doc_types=doc_types)


# ── Employee Approval Requests Workflow ──────────────────────────────
@admin_bp.route('/approvals')
@admin_required
def approvals_list():
    """Queue of all pending approval requests submitted by employees."""
    page = request.args.get('page', 1, type=int)
    query = ApprovalRequest.query.filter_by(status='Pending')
    
    pagination = query.order_by(ApprovalRequest.created_at.asc()).paginate(
        page=page, per_page=10, error_out=False
    )
    requests = pagination.items
    
    return render_template('admin/approvals/list.html', requests=requests, pagination=pagination)


@admin_bp.route('/approvals/<int:id>/review', methods=['GET', 'POST'])
@admin_required
def review_approval(id):
    """Review details and compare diffs before approving or rejecting."""
    req = ApprovalRequest.query.get_or_404(id)
    if req.status != 'Pending':
        flash('This request has already been reviewed.', 'warning')
        return redirect(url_for('admin.approvals_list'))
        
    prev = json.loads(req.previous_values) if req.previous_values else {}
    proposed = json.loads(req.proposed_values) if req.proposed_values else {}
    
    if request.method == 'POST':
        action = request.form.get('action')
        reason = request.form.get('rejection_reason', '').strip()
        
        if action == 'approve':
            req.status = 'Approved'
            req.reviewed_at = datetime.now(timezone.utc)
            req.reviewed_by_id = current_user.id
            
            # Apply changes depending on request type
            doc = req.document
            
            if req.request_type == 'Upload':
                doc.approved = True
                doc.approved_by_id = current_user.id
                
            elif req.request_type == 'Replace':
                # Archive current doc state into history version
                history = DocumentVersion(
                    document_id=doc.id,
                    version_number=doc.upload_version,
                    cloudinary_public_id=doc.cloudinary_public_id,
                    cloudinary_url=doc.cloudinary_url,
                    original_filename=doc.original_filename,
                    file_size=doc.file_size,
                    file_hash=doc.file_hash,
                    uploaded_by_id=doc.uploaded_by_id
                )
                db.session.add(history)
                
                # Apply replacement file details
                doc.cloudinary_public_id = proposed['cloudinary_public_id']
                doc.cloudinary_url = proposed['cloudinary_url']
                doc.original_filename = proposed['original_filename']
                doc.file_size = proposed['file_size']
                doc.file_hash = proposed['file_hash']
                doc.uploaded_by_id = req.employee_id
                doc.upload_version += 1
                
            elif req.request_type == 'Metadata Edit':
                doc.title = proposed['title']
                doc.description = proposed.get('description')
                doc.document_type = proposed['document_type']
                doc.financial_year = proposed['financial_year']
                
            elif req.request_type == 'Delete':
                doc.status = 'Deleted'
                
            elif req.request_type == 'Password Change':
                doc.password_protected = proposed['password_protected']
                if proposed.get('pdf_password'):
                    doc.pdf_password = proposed['pdf_password']
                else:
                    doc.pdf_password = None
                    
            db.session.commit()
            
            # Note: doc might be None if request type was Delete and doc was already deleted, but req.document should be there if relationships are setup.
            # Using client_id from the original request or document if available.
            client_id = doc.client_id if doc else req.employee_id # Fallback
            if doc:
                create_timeline_event(
                    client_id=doc.client_id,
                    event_type='Approval Request Approved',
                    description=f'{req.request_type} request approved by {current_user.full_name}.',
                    user_id=current_user.id,
                    document_id=doc.id
                )
                db.session.commit()
                
            create_notification(req.employee_id, f"Your '{req.request_type}' request for '{doc.title if doc else 'Document'}' was Approved.", link=url_for('employee.requests_list'), title='Request Approved', category='approvals', priority='high', entity_type='ApprovalRequest', entity_id=req.id)
                
            log_user_action(logger, current_user, f'approve_{req.request_type.lower()}', module='approvals', entity_type='ApprovalRequest', entity_id=req.id, description=f'Approved request {req.id}')
            flash('Employee request approved successfully.', 'success')
            return redirect(url_for('admin.approvals_list'))
            
        elif action == 'reject':
            if not reason:
                flash('Please provide a reason for rejection.', 'danger')
                return render_template('admin/approvals/review.html', req=req, prev=prev, proposed=proposed)
                
            req.status = 'Rejected'
            req.rejection_reason = reason
            req.reviewed_at = datetime.now(timezone.utc)
            req.reviewed_by_id = current_user.id
            
            # Clean up Cloudinary file if it was a draft Upload or Replace
            if req.request_type == 'Upload' and req.document:
                # Delete draft Document row and Cloudinary link
                delete_pdf(req.document.cloudinary_public_id)
                db.session.delete(req.document)
            elif req.request_type == 'Replace':
                # Delete the proposed replacement file from Cloudinary
                delete_pdf(proposed['cloudinary_public_id'])
                
            db.session.commit()
            
            if req.document:
                create_timeline_event(
                    client_id=req.document.client_id,
                    event_type='Approval Request Rejected',
                    description=f'{req.request_type} request rejected. Reason: {reason}',
                    user_id=current_user.id,
                    document_id=req.document.id
                )
                db.session.commit()
                
            create_notification(req.employee_id, f"Your '{req.request_type}' request was Rejected. Reason: {reason}", link=url_for('employee.requests_list'), title='Request Rejected', category='approvals', priority='high', entity_type='ApprovalRequest', entity_id=req.id)
                
            log_user_action(logger, current_user, f'reject_{req.request_type.lower()}', module='approvals', entity_type='ApprovalRequest', entity_id=req.id, description=f'Rejected request {req.id} for {reason}')
            flash('Employee request rejected and logged.', 'info')
            return redirect(url_for('admin.approvals_list'))
            
    return render_template('admin/approvals/review.html', req=req, prev=prev, proposed=proposed)
