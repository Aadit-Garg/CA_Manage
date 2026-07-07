from flask import render_template, request
from flask_login import current_user
from ..auth.decorators import admin_required
from ..models.audit import AuditLog
from . import admin_bp

@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    """View system audit logs."""
    page = request.args.get('page', 1, type=int)
    
    # Optional filters
    user_role = request.args.get('user_role', '')
    module = request.args.get('module', '')
    action = request.args.get('action', '')
    
    query = AuditLog.query
    
    if user_role:
        query = query.filter(AuditLog.user_role == user_role)
    if module:
        query = query.filter(AuditLog.module == module)
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
        
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    
    return render_template(
        'admin/audit/list.html',
        logs=pagination.items,
        pagination=pagination,
        user_role=user_role,
        module=module,
        action=action
    )
