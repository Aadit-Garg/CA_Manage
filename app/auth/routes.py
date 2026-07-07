"""
CA Manage — Authentication Routes

Login, logout, and password change with rate limiting and security logging.
"""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db, limiter
from . import auth_bp
from .forms import LoginForm, ChangePasswordForm
from ..models.user import User


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('50 per minute')
def login():
    """Handle user login."""
    # Already logged in? Redirect to dashboard
    if current_user.is_authenticated:
        return redirect(_dashboard_url())

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                current_app.logger.warning(f'Login attempt for deactivated account: {user.email}')
                return render_template('auth/login.html', form=form)

            # Successful login
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.now(timezone.utc)
            user.failed_login_attempts = 0  # Reset attempts on success
            db.session.commit()
            current_app.logger.info(f'User logged in: {user.email} [{user.role}]')

            # Redirect to requested page or role-based dashboard
            next_page = request.args.get('next')
            if next_page and _is_safe_url(next_page):
                return redirect(next_page)
            return redirect(_dashboard_url())
        else:
            if user:
                user.failed_login_attempts += 1
                db.session.commit()
            flash('Invalid email or password.', 'danger')
            current_app.logger.warning(
                f'Failed login attempt for email: {form.email.data} from IP: {request.remote_addr}'
            )

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user and clear session."""
    current_app.logger.info(f'User logged out: {current_user.email}')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow authenticated users to change their password."""
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        current_app.logger.info(f'Password changed for user: {current_user.email}')
        flash('Password updated successfully.', 'success')
        return redirect(_dashboard_url())

    return render_template('auth/change_password.html', form=form)


# ── Helpers ─────────────────────────────────────────────────────────

def _dashboard_url():
    """Return the URL for the current user's role-specific dashboard."""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return url_for('admin.dashboard')
        elif current_user.role == 'employee':
            return url_for('employee.dashboard')
        elif current_user.role == 'client':
            return url_for('client_portal.dashboard')
    return url_for('auth.login')


def _is_safe_url(target):
    """Validate that the redirect target is safe (same origin)."""
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
