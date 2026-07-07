"""
CA Manage — Logging Utilities

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


def log_user_action(logger, user, action, details=None):
    """
    Log a user action in a structured format for audit trail.

    Args:
        logger: Logger instance
        user: Current user object
        action: Action description (e.g., 'login', 'upload_document')
        details: Optional dict with additional context
    """
    msg = f'[USER_ACTION] user={user.email} role={user.role} action={action}'
    if details:
        detail_str = ' '.join(f'{k}={v}' for k, v in details.items())
        msg += f' {detail_str}'
    logger.info(msg)
