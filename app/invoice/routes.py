from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from . import invoice_bp
from app.models.invoice import Invoice, InvoiceItem
from app.models.client import ClientProfile
from app.models.settings import FirmSettings
from functools import wraps

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@invoice_bp.route('/', methods=['GET'])
@login_required
@role_required('admin', 'employee')
def dashboard():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(10).all()
    clients_count = ClientProfile.query.count()
    invoices_count = Invoice.query.count()
    return render_template('invoice/dashboard.html', invoices=invoices, clients_count=clients_count, invoices_count=invoices_count)

@invoice_bp.route('/list', methods=['GET'])
@login_required
@role_required('admin', 'employee')
def invoices():
    all_invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('invoice/invoices.html', invoices=all_invoices)

@invoice_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def new_invoice():
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        invoice_number = request.form.get('invoice_number')
        issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date()
        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        tax_type = request.form.get('tax_type')
        notes = request.form.get('notes')
        
        invoice = Invoice(
            client_id=client_id,
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=due_date,
            tax_type=tax_type,
            notes=notes,
            client_name=request.form.get('client_name'),
            client_address=request.form.get('client_address'),
            client_gstin=request.form.get('client_gstin'),
            client_pan=request.form.get('client_pan'),
            firm_name=request.form.get('firm_name_override') or None,
            firm_address=request.form.get('firm_address_override') or None,
            bank_account_name=request.form.get('bank_account_name_override') or None,
            bank_name=request.form.get('bank_name_override') or None,
            account_number=request.form.get('account_number_override') or None,
            ifsc_code=request.form.get('ifsc_code_override') or None
        )
        db.session.add(invoice)
        db.session.flush() # get invoice ID
        
        # Add items
        descriptions = request.form.getlist('description[]')
        sac_codes = request.form.getlist('sac_code[]')
        amounts = request.form.getlist('amount[]')
        
        for i in range(len(descriptions)):
            if descriptions[i].strip() and amounts[i].strip():
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=descriptions[i],
                    sac_code=sac_codes[i],
                    amount=float(amounts[i])
                )
                db.session.add(item)
                
        # Log action and timeline event
        from app.utils.logging import log_user_action
        from app.utils.timeline import create_timeline_event
        from flask import current_app
        
        log_user_action(current_app.logger, current_user, 'create_invoice', 'invoices', 'Invoice', invoice.id, f'Created invoice {invoice.invoice_number}')
        
        if invoice.client_id:
            create_timeline_event(
                client_id=invoice.client_id,
                event_type='Invoice Created',
                description=f'Created invoice {invoice.invoice_number}',
                user_id=current_user.id
            )
            
        db.session.commit()
        
        flash('Invoice created successfully', 'success')
        return redirect(url_for('invoice.invoices'))
        
    client_records = ClientProfile.query.all()
    clients = []
    for c in client_records:
        clients.append({
            'id': c.id,
            'name': c.firm_name or c.full_name,
            'address': f"{c.address or ''}, {c.city or ''}, {c.state or ''} - {c.pincode or ''}".strip(' ,-'),
            'gstin': getattr(c, 'GST', getattr(c, 'gstin', '')),
            'pan': getattr(c, 'PAN', getattr(c, 'pan', ''))
        })
    # Generate next invoice number
    last_inv = Invoice.query.order_by(Invoice.id.desc()).first()
    next_num = f"INV-{datetime.now().strftime('%Y%m')}-{(last_inv.id + 1 if last_inv else 1):03d}"
    
    return render_template('invoice/invoice_form.html', clients=clients, next_num=next_num, today=datetime.now().strftime('%Y-%m-%d'))

@invoice_bp.route('/<int:id>')
@login_required
def view_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoice/invoice_view.html', invoice=invoice)

@invoice_bp.route('/<int:id>/print')
@login_required
def print_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoice/invoice_print.html', invoice=invoice)

@invoice_bp.route('/<int:id>/share', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def share_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    if invoice.status == 'Draft':
        invoice.status = 'Unpaid'
        
        # Log action and notify client
        from app.utils.logging import log_user_action
        from app.utils.notification import create_notification
        from app.utils.timeline import create_timeline_event
        from flask import current_app
        
        log_user_action(current_app.logger, current_user, 'share_invoice', 'invoice', 'Invoice', invoice.id, f'Shared invoice {invoice.invoice_number}')
        
        if invoice.client_id:
            client = ClientProfile.query.get(invoice.client_id)
            if client and client.user_id:
                create_notification(
                    user_id=client.user_id,
                    message=f"A new invoice ({invoice.invoice_number}) has been shared with you.",
                    link=url_for('client_portal.view_invoice', id=invoice.id),
                    title='New Invoice Available',
                    category='general',
                    priority='high',
                    entity_type='Invoice',
                    entity_id=invoice.id
                )
                
        db.session.commit()
        flash('Invoice shared with client successfully!', 'success')
    else:
        flash('Invoice is already shared.', 'info')
        
    return redirect(url_for('invoice.view_invoice', id=invoice.id))

@invoice_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def edit_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    if request.method == 'POST':
        invoice.invoice_number = request.form.get('invoice_number')
        invoice.issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date()
        due_date_str = request.form.get('due_date')
        invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        invoice.tax_type = request.form.get('tax_type')
        invoice.notes = request.form.get('notes')
        
        # Update client snapshot if changed
        new_client_id = request.form.get('client_id')
        if new_client_id and str(new_client_id) != str(invoice.client_id):
            invoice.client_id = new_client_id
            invoice.client_name = request.form.get('client_name')
            invoice.client_address = request.form.get('client_address')
            invoice.client_gstin = request.form.get('client_gstin')
            invoice.client_pan = request.form.get('client_pan')
            
        # Overrides
        invoice.firm_name = request.form.get('firm_name_override') or None
        invoice.firm_address = request.form.get('firm_address_override') or None
        invoice.bank_account_name = request.form.get('bank_account_name_override') or None
        invoice.bank_name = request.form.get('bank_name_override') or None
        invoice.account_number = request.form.get('account_number_override') or None
        invoice.ifsc_code = request.form.get('ifsc_code_override') or None
        
        # Recreate items
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        descriptions = request.form.getlist('description[]')
        sac_codes = request.form.getlist('sac_code[]')
        amounts = request.form.getlist('amount[]')
        
        for i in range(len(descriptions)):
            if descriptions[i].strip() and amounts[i].strip():
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=descriptions[i],
                    sac_code=sac_codes[i],
                    amount=float(amounts[i])
                )
                db.session.add(item)
                
        # Log action and timeline event
        from app.utils.logging import log_user_action
        from app.utils.timeline import create_timeline_event
        from flask import current_app
        
        log_user_action(current_app.logger, current_user, 'edit_invoice', 'invoices', 'Invoice', invoice.id, f'Updated invoice {invoice.invoice_number}')
        
        if invoice.client_id:
            create_timeline_event(
                client_id=invoice.client_id,
                event_type='Invoice Updated',
                description=f'Updated invoice {invoice.invoice_number}',
                user_id=current_user.id
            )
            
        db.session.commit()
        
        flash('Invoice updated successfully', 'success')
        return redirect(url_for('invoice.view_invoice', id=invoice.id))

    client_records = ClientProfile.query.all()
    clients = []
    for c in client_records:
        clients.append({
            'id': c.id,
            'name': c.firm_name or c.full_name,
            'address': f"{c.address or ''}, {c.city or ''}, {c.state or ''} - {c.pincode or ''}".strip(' ,-'),
            'gstin': getattr(c, 'GST', getattr(c, 'gstin', '')),
            'pan': getattr(c, 'PAN', getattr(c, 'pan', ''))
        })
    return render_template('invoice/invoice_form.html', invoice=invoice, clients=clients)

@invoice_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Log action and timeline event before deletion
    from app.utils.logging import log_user_action
    from app.utils.timeline import create_timeline_event
    from flask import current_app
    
    log_user_action(current_app.logger, current_user, 'delete_invoice', 'invoices', 'Invoice', invoice.id, f'Deleted invoice {invoice.invoice_number}')
    
    if invoice.client_id:
        create_timeline_event(
            client_id=invoice.client_id,
            event_type='Invoice Deleted',
            description=f'Deleted invoice {invoice.invoice_number}',
            user_id=current_user.id
        )
        
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted successfully', 'success')
    return redirect(url_for('invoice.invoices'))
