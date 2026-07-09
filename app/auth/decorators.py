"""
Sumit n Garg & Associates — Role-Based Access Control Decorators

Provides reusable decorators that enforce role checks on top of Flask-Login's
@login_required. Stack these on any route that needs role protection.
"""
from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    """
    Decorator factory that restricts access to users with specific roles.

    Usage:
        @role_required('admin', 'employee')
        def some_view():
            ...

    Always use AFTER @login_required in the decorator stack, or use the
    convenience shortcuts below which handle both.
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            if not current_user.is_active:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Restrict to administrators only."""
    @wraps(f)
    @role_required('admin')
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def employee_required(f):
    """Restrict to employees and administrators."""
    @wraps(f)
    @role_required('admin', 'employee')
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def client_required(f):
    """Restrict to clients only."""
    @wraps(f)
    @role_required('client')
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function
