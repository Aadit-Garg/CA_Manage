"""
CA Manage — User Model

Unified user model for all three roles: admin, employee, client.
Uses Werkzeug for secure password hashing.
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db


class User(UserMixin, db.Model):
    """
    Core user model.

    Roles:
        - admin: Full system access
        - employee: Document management, attendance, assigned clients
        - client: View/download own documents only
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='client', index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    client_profile = db.relationship('ClientProfile', backref='user', uselist=False,
                                     lazy='joined', cascade='all, delete-orphan',
                                     foreign_keys='ClientProfile.user_id')
    employee_profile = db.relationship('Employee', backref='user', uselist=False,
                                       lazy='joined', cascade='all, delete-orphan',
                                       foreign_keys='Employee.user_id')
    assigned_clients = db.relationship('ClientProfile', backref='assigned_employee',
                                       lazy='dynamic',
                                       foreign_keys='ClientProfile.assigned_employee_id')

    # ── Valid roles ─────────────────────────────────────────────────
    ROLE_ADMIN = 'admin'
    ROLE_EMPLOYEE = 'employee'
    ROLE_CLIENT = 'client'
    VALID_ROLES = (ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_CLIENT)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.role not in self.VALID_ROLES:
            raise ValueError(f'Invalid role: {self.role}. Must be one of {self.VALID_ROLES}')

    # ── Password management ─────────────────────────────────────────
    def set_password(self, password):
        """Hash and store the password using pbkdf2:sha256."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        self.password_changed_at = datetime.now(timezone.utc)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # ── Role checks ─────────────────────────────────────────────────
    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_employee(self):
        return self.role == self.ROLE_EMPLOYEE

    @property
    def is_client(self):
        return self.role == self.ROLE_CLIENT

    # ── Flask-Login integration ─────────────────────────────────────
    def get_id(self):
        return str(self.id)

    @property
    def is_active_user(self):
        """Override for Flask-Login — deactivated users cannot log in."""
        return self.is_active

    # ── Display ─────────────────────────────────────────────────────
    @property
    def display_role(self):
        """Human-readable role name."""
        return self.role.capitalize()

    @property
    def initials(self):
        """Get user initials for avatar placeholder."""
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.full_name[0:2].upper()

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'
