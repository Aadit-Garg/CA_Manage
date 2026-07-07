"""
CA Manage — Authentication Routes

Login, logout, and password change with rate limiting and security logging.
"""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..models.user import User
from ..models.push_subscription import PushSubscription
from ..models.notification import Notification
from ..extensions import db, limiter
from . import auth_bp
from .forms import LoginForm, ChangePasswordForm


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


@auth_bp.route('/notifications/vapid-public-key', methods=['GET'])
@login_required
def vapid_public_key():
    import os
    return jsonify({'public_key': os.environ.get('VAPID_PUBLIC_KEY')})


@auth_bp.route('/notifications/subscribe', methods=['POST'])
@login_required
def subscribe():
    """Saves a PushSubscription for the current user."""
    subscription_info = request.json
    if not subscription_info:
        return jsonify({'error': 'Invalid payload'}), 400

    endpoint = subscription_info.get('endpoint')
    keys = subscription_info.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({'error': 'Missing subscription details'}), 400

    # Check if this endpoint already exists for this user
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        if existing.user_id != current_user.id:
            existing.user_id = current_user.id
            db.session.commit()
        return jsonify({'status': 'Subscription already exists and is valid'}), 200

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({'status': 'Subscribed successfully'}), 201


@auth_bp.route('/notifications/read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    """Marks a single notification as read."""
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'status': 'success'})

@auth_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marks all notifications for user as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'success'})
