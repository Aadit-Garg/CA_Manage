"""
Sumit N Garg & Associates — Logging Utilities

Helper functions for structured application logging.
The main logging config is in app/__init__.py (configure_logging).
"""
import logging


def get_logger(name):
    """
    Get a namespaced logger for a module.

    Usage:
        from app.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info('Something happened')
    """
    return logging.getLogger(f'ca_manage.{name}')


def log_user_action(logger, user, action, module='system', entity_type=None, entity_id=None, description='', old_values=None, new_values=None, details=None):
    """
    Log a user action in a structured format for audit trail, and save an AuditLog record to the database.
    """
    from flask import request, has_request_context
    from ..extensions import db
    from ..models.audit import AuditLog

    # Create the text log
    msg = f'[USER_ACTION] user={user.email if user else "system"} role={user.role if user else "system"} action={action}'
    if details:
        detail_str = ' '.join(f'{k}={v}' for k, v in details.items())
        msg += f' {detail_str}'
    if description:
        msg += f' | desc={description}'
    logger.info(msg)

    # Capture Request Info
    ip_address = None
    user_agent = None
    if has_request_context():
        ip_address = request.remote_addr
        user_agent = request.user_agent.string[:255]

    # Save to Database
    try:
        audit = AuditLog(
            user_id=user.id if user else None,
            user_role=user.role if user else 'system',
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            description=description or msg,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to write AuditLog to database: {e}")
        db.session.rollback()
