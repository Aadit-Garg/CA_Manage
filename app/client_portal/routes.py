"""
CA Manage — Client Portal Dashboard & Settings Routes

Enables clients to view their dashboard, inspect their profile, change their password,
and securely view, search, filter, preview, and download their approved documents.
"""
import requests
import io
from flask import render_template, redirect, url_for, flash, request, Response, session
from flask_login import current_user
from ..auth.decorators import client_required
from ..auth.forms import ChangePasswordForm
from ..admin.forms import PasswordGatewayForm
from ..extensions import db
from ..models.document import Document
from ..models.client import ClientProfile
from werkzeug.security import check_password_hash
from . import client_bp


@client_bp.route('/dashboard')
@client_required
def dashboard():
    """Client dashboard with document overview and account info summary."""
    # Count approved documents
    client_profile = current_user.client_profile
    total_docs = Document.query.filter_by(
        client_id=client_profile.id,
        approved=True,
        status='Active'
    ).count()

    stats = {
        'total_documents': total_docs,
        'recent_documents': 0,    # Will hold recent uploads
        'pending_documents': 0,
    }

    # Latest approved uploads
    latest_uploads = Document.query.filter_by(
        client_id=client_profile.id,
        approved=True,
        status='Active'
    ).order_by(Document.created_at.desc()).limit(5).all()

    # Document categories
    categories = [
        {'name': 'Income Tax Return', 'icon': 'bi-file-earmark-text', 'count': Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active', document_type='Income Tax Return').count(), 'color': 'primary'},
        {'name': 'GST Return', 'icon': 'bi-receipt', 'count': Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active', document_type='GST Return').count(), 'color': 'success'},
        {'name': 'Audit Report', 'icon': 'bi-clipboard-check', 'count': Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active', document_type='Audit Report').count(), 'color': 'info'},
        {'name': 'Balance Sheet', 'icon': 'bi-graph-up', 'count': Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active', document_type='Balance Sheet').count(), 'color': 'warning'},
        {'name': 'Invoices', 'icon': 'bi-file-earmark-ruled', 'count': Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active', document_type='Invoice').count(), 'color': 'danger'},
        {'name': 'Other', 'icon': 'bi-folder2-open', 'count': Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active', document_type='Other').count(), 'color': 'secondary'},
    ]

    return render_template(
        'client/dashboard.html',
        stats=stats,
        categories=categories,
        profile=client_profile,
        latest_uploads=latest_uploads
    )


@client_bp.route('/profile')
@client_required
def view_profile():
    """Client views their own profile page."""
    profile = current_user.client_profile
    return render_template('client/profile.html', client=profile)


@client_bp.route('/change-password', methods=['GET', 'POST'])
@client_required
def change_password():
    """Client changes their own password with validation."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user = current_user
        if user.check_password(form.current_password.data):
            user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('client_portal.dashboard'))
        else:
            flash('Invalid current password.', 'danger')

    return render_template('client/change_password.html', form=form)


# ── Document Access ──────────────────────────────────────────────────
@client_bp.route('/documents')
@client_required
def documents_list():
    """Search, filter, and paginate approved documents belonging to the client."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    doc_type = request.args.get('type', '').strip()
    financial_year = request.args.get('year', '').strip()

    client_profile = current_user.client_profile
    query = Document.query.filter_by(client_id=client_profile.id, approved=True, status='Active')

    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if financial_year:
        query = query.filter(Document.financial_year == financial_year)
    if search:
        query = query.filter(
            db.or_(
                Document.title.ilike(f'%{search}%'),
                Document.description.ilike(f'%{search}%'),
                Document.tags.ilike(f'%{search}%'),
                Document.original_filename.ilike(f'%{search}%')
            )
        )

    pagination = query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    documents = pagination.items

    # Fetch unique categories/years for filters
    doc_types = Document.sensible_defaults
    financial_years = ['2023-24', '2024-25', '2025-26', '2026-27']

    return render_template(
        'client/documents/list.html',
        documents=documents,
        pagination=pagination,
        search=search,
        selected_type=doc_type,
        selected_year=financial_year,
        doc_types=doc_types,
        financial_years=financial_years
    )


@client_bp.route('/documents/<int:id>/unlock', methods=['GET', 'POST'])
@client_required
def unlock_document(id):
    """Gated form to input password for protected document access."""
    client_profile = current_user.client_profile
    doc = Document.query.filter_by(id=id, client_id=client_profile.id, approved=True, status='Active').first_or_404()
    
    if not doc.password_protected:
        return redirect(url_for('client_portal.download_document', id=doc.id))

    form = PasswordGatewayForm()
    if form.validate_on_submit():
        if check_password_hash(doc.pdf_password, form.password.data):
            # Unlock document for the session
            unlocked = session.get('unlocked_documents', [])
            if doc.id not in unlocked:
                unlocked.append(doc.id)
                session['unlocked_documents'] = unlocked
            
            # Check if requesting download or preview
            action = request.args.get('action', 'download')
            if action == 'preview':
                return redirect(url_for('client_portal.preview_document', id=doc.id))
            return redirect(url_for('client_portal.download_document', id=doc.id))
        else:
            flash('Incorrect document password.', 'danger')

    return render_template('client/documents/unlock.html', form=form, document=doc)


@client_bp.route('/documents/<int:id>/download')
@client_required
def download_document(id):
    """Proxied download route to securely redirect to Cloudinary, verifying password protection."""
    import urllib.parse
    client_profile = current_user.client_profile
    doc = Document.query.filter_by(id=id, client_id=client_profile.id, approved=True, status='Active').first_or_404()
    
    if doc.password_protected:
        unlocked = session.get('unlocked_documents', [])
        if doc.id not in unlocked:
            return redirect(url_for('client_portal.unlock_document', id=doc.id, action='download'))

    safe_filename = urllib.parse.quote(doc.original_filename)
    url = doc.cloudinary_url
    if '/raw/upload/' in url:
        url = url.replace('/raw/upload/', '/image/upload/')
    download_url = url.replace('/upload/', f'/upload/fl_attachment:{safe_filename}/')
    return redirect(download_url)


@client_bp.route('/documents/<int:id>/preview')
@client_required
def preview_document(id):
    """Proxied inline preview route to securely redirect to Cloudinary, verifying password protection."""
    client_profile = current_user.client_profile
    doc = Document.query.filter_by(id=id, client_id=client_profile.id, approved=True, status='Active').first_or_404()
    
    if doc.password_protected:
        unlocked = session.get('unlocked_documents', [])
        if doc.id not in unlocked:
            return redirect(url_for('client_portal.unlock_document', id=doc.id, action='preview'))

    url = doc.cloudinary_url
    if '/raw/upload/' in url:
        url = url.replace('/raw/upload/', '/image/upload/')
    return redirect(url)
