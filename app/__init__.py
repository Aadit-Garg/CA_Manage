"""
Sumit N Garg & Associates — Application Factory

Creates and configures the Flask application.
Registers all extensions, blueprints, error handlers, and shell context.
"""
import os
import logging
from flask import Flask, send_from_directory
from .config import config_map
from .extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name=None):
    """
    Application factory.

    Args:
        config_name: One of 'development', 'production', 'testing'.
                     Defaults to FLASK_ENV environment variable or 'development'.
    """
    app = Flask(__name__)
    
    # Apply ProxyFix so Flask knows it is behind an HTTPS reverse proxy (Vercel)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ── Load configuration ──────────────────────────────────────────
    if config_name is None:
        # Auto-detect Vercel serverless environment
        if os.environ.get('VERCEL') == '1':
            config_name = 'production'
        else:
            config_name = os.getenv('FLASK_ENV', 'development')
    config_class = config_map.get(config_name, config_map['default'])
    app.config.from_object(config_class)

    # Run production safety checks
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)

    # ── Initialize extensions ───────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # ── Register user loader ────────────────────────────────────────
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Register blueprints ─────────────────────────────────────────
    from .auth import auth_bp
    from .admin import admin_bp
    from .employee import employee_bp
    from .client_portal import client_bp
    from .errors import errors_bp
    from .api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(employee_bp, url_prefix='/employee')
    app.register_blueprint(client_bp, url_prefix='/client')
    app.register_blueprint(api_bp)
    app.register_blueprint(errors_bp)

    # ── Root route ──────────────────────────────────────────────────
    from flask import redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def index():
        """Redirect to role-appropriate dashboard or login."""
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'employee':
                return redirect(url_for('employee.dashboard'))
            elif current_user.role == 'client':
                return redirect(url_for('client_portal.dashboard'))
        return redirect(url_for('auth.login'))

    @app.before_request
    def enforce_security_checks():
        from flask import request, session, flash, redirect, url_for
        
        if current_user.is_authenticated:
            # 1. Enforce Expiration Date for Clients
            if current_user.role == 'client' and current_user.client_profile and current_user.client_profile.is_expired:
                from flask_login import logout_user
                logout_user()
                flash('Your account login has expired. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.login'))

    # ── PWA routes (serve at root path) ─────────────────────────────
    @app.route('/manifest.json')
    def serve_manifest():
        return send_from_directory(
            app.static_folder, 'manifest.json',
            mimetype='application/manifest+json'
        )

    @app.route('/sw.js')
    def serve_sw():
        return send_from_directory(
            app.static_folder, 'sw.js',
            mimetype='application/javascript'
        )

    # ── Template context processors ─────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {
            'app_name': app.config.get('APP_NAME', 'Sumit N Garg & Associates'),
            'app_description': app.config.get('APP_DESCRIPTION', ''),
        }

    # ── Jinja Filters ───────────────────────────────────────────────
    from .utils.timezone import to_ist
    app.jinja_env.filters['ist'] = to_ist

    # ── Shell context ───────────────────────────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        from .models.user import User
        from .models.client import ClientProfile
        from .models.employee import Employee
        from .models.document import Document
        from .models.document_version import DocumentVersion
        from .models.approval import ApprovalRequest
        return {
            'db': db, 
            'User': User, 
            'ClientProfile': ClientProfile, 
            'Employee': Employee,
            'Document': Document,
            'DocumentVersion': DocumentVersion,
            'ApprovalRequest': ApprovalRequest
        }

    # ── Logging ─────────────────────────────────────────────────────
    configure_logging(app)

    return app


def configure_logging(app):
    """Set up application logging with file and stream handlers."""
    log_level = logging.DEBUG if app.debug else logging.INFO

    # Stream handler (always enabled)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))
    stream_handler.setLevel(log_level)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(log_level)

    # Skip file logging on Vercel (read-only file system)
    if os.environ.get('VERCEL') == '1':
        app.logger.info('Sumit N Garg & Associates application started (Vercel Mode - Stream Logging Only)')
        return

    try:
        # Create logs directory
        log_dir = os.path.join(os.path.dirname(app.root_path), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'ca_manage.log'),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
    except Exception as e:
        app.logger.warning(f'Could not configure file logging: {e}')

    app.logger.info('Sumit N Garg & Associates application started')
