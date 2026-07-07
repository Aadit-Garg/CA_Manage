"""
CA Manage — Authentication Forms

WTForms for login and password change with CSRF protection.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp


class LoginForm(FlaskForm):
    """Login form with email + password."""
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
    ], render_kw={
        'placeholder': 'you@example.com',
        'autocomplete': 'email',
        'autofocus': True,
        'class': 'form-control form-control-lg',
        'inputmode': 'email',
    })
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
    ], render_kw={
        'placeholder': '••••••••',
        'autocomplete': 'current-password',
        'class': 'form-control form-control-lg',
    })
    
    remember_me = BooleanField('Remember me', render_kw={
        'class': 'form-check-input',
    })
    
    submit = SubmitField('Sign In', render_kw={
        'class': 'btn btn-primary btn-lg w-100',
    })


class ChangePasswordForm(FlaskForm):
    """Password change form for authenticated users."""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required'),
    ], render_kw={
        'placeholder': 'Enter current password',
        'autocomplete': 'current-password',
        'class': 'form-control form-control-lg',
    })
    
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            message='Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character (@$!%*?&).'
        )
    ], render_kw={
        'placeholder': 'At least 8 characters',
        'autocomplete': 'new-password',
        'class': 'form-control form-control-lg',
    })
    
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match'),
    ], render_kw={
        'placeholder': 'Re-enter new password',
        'autocomplete': 'new-password',
        'class': 'form-control form-control-lg',
    })
    
    submit = SubmitField('Update Password', render_kw={
        'class': 'btn btn-primary btn-lg w-100',
    })
