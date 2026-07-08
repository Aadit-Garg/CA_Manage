from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp, ValidationError
from ..models.user import User
from ..models.client import ClientProfile

class EmployeeForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Full Name is required'),
        Length(max=150)
    ], render_kw={'class': 'form-control'})
    
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email format'),
        Length(max=255)
    ], render_kw={'class': 'form-control'})
    
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20)
    ], render_kw={'class': 'form-control'})
    
    designation = StringField('Designation', validators=[
        Optional(),
        Length(max=100)
    ], render_kw={'class': 'form-control'})
    
    joining_date = DateField('Joining Date', validators=[
        Optional()
    ], format='%Y-%m-%d', render_kw={'class': 'form-control', 'type': 'date'})
    
    notes = TextAreaField('Notes', validators=[
        Optional()
    ], render_kw={'class': 'form-control', 'rows': 3})
    
    submit = SubmitField('Save Employee', render_kw={'class': 'btn btn-primary'})

    def __init__(self, original_user_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user_id = original_user_id

    def validate_email(self, email):
        email_clean = email.data.lower().strip()
        q = User.query.filter_by(email=email_clean)
        if self.original_user_id:
            q = q.filter(User.id != self.original_user_id)
        if q.first():
            raise ValidationError('Email address is already registered.')


class SystemAdminForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Full Name is required'),
        Length(max=150)
    ], render_kw={'class': 'form-control'})
    
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email format'),
        Length(max=255)
    ], render_kw={'class': 'form-control'})
    
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20)
    ], render_kw={'class': 'form-control'})
    
    submit = SubmitField('Save System Admin', render_kw={'class': 'btn btn-primary'})

    def __init__(self, original_user_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user_id = original_user_id

    def validate_email(self, email):
        email_clean = email.data.lower().strip()
        q = User.query.filter_by(email=email_clean)
        if self.original_user_id:
            q = q.filter(User.id != self.original_user_id)
        if q.first():
            raise ValidationError('Email address is already registered.')


class ClientForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Full Name is required'),
        Length(max=150)
    ], render_kw={'class': 'form-control'})
    
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email format'),
        Length(max=255)
    ], render_kw={'class': 'form-control'})
    
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20)
    ], render_kw={'class': 'form-control'})
    
    firm_name = StringField('Firm Name', validators=[
        Optional(),
        Length(max=200)
    ], render_kw={'class': 'form-control'})
    
    client_type = SelectField('Client Type', choices=[
        ('individual', 'Individual'),
        ('business', 'Business')
    ], render_kw={'class': 'form-select'})

    PAN = StringField('PAN', validators=[
        Optional(),
        Regexp(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', message='Invalid PAN. e.g. ABCDE1234F')
    ], render_kw={'class': 'form-control', 'style': 'text-transform: uppercase;'})
    
    GST = StringField('GSTIN', validators=[
        Optional(),
        Regexp(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', 
               message='Invalid GSTIN. e.g. 27ABCDE1234F1Z5')
    ], render_kw={'class': 'form-control', 'style': 'text-transform: uppercase;'})
    
    address = TextAreaField('Address', validators=[
        Optional()
    ], render_kw={'class': 'form-control', 'rows': 2})
    
    city = StringField('City', validators=[
        Optional(),
        Length(max=100)
    ], render_kw={'class': 'form-control'})
    
    state = StringField('State', validators=[
        Optional(),
        Length(max=100)
    ], render_kw={'class': 'form-control'})
    
    pincode = StringField('Pincode', validators=[
        Optional(),
        Length(max=10)
    ], render_kw={'class': 'form-control'})
    
    assigned_employee_id = SelectField('Assigned Employee', coerce=int, render_kw={'class': 'form-select'})
    
    notes = TextAreaField('Notes', validators=[
        Optional()
    ], render_kw={'class': 'form-control', 'rows': 3})
    
    submit = SubmitField('Save Client', render_kw={'class': 'btn btn-primary'})

    def __init__(self, original_user_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user_id = original_user_id
        
        # Dynamically load active employees for assignment
        employees = User.query.filter_by(role='employee', is_active=True).all()
        self.assigned_employee_id.choices = [(0, 'Unassigned')] + [(e.id, e.full_name) for e in employees]

    def validate_email(self, email):
        email_clean = email.data.lower().strip()
        q = User.query.filter_by(email=email_clean)
        if self.original_user_id:
            q = q.filter(User.id != self.original_user_id)
        if q.first():
            raise ValidationError('Email address is already registered.')

    def validate_PAN(self, PAN):
        if PAN.data:
            pan_clean = PAN.data.upper().strip()
            q = ClientProfile.query.filter_by(PAN=pan_clean)
            if self.original_user_id:
                q = q.filter(ClientProfile.user_id != self.original_user_id)
            if q.first():
                raise ValidationError('PAN is already registered to another client.')

    def validate_GST(self, GST):
        if GST.data:
            gst_clean = GST.data.upper().strip()
            q = ClientProfile.query.filter_by(GST=gst_clean)
            if self.original_user_id:
                q = q.filter(ClientProfile.user_id != self.original_user_id)
            if q.first():
                raise ValidationError('GSTIN is already registered to another client.')


class AdminResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            message='Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character (@$!%*?&).'
        )
    ], render_kw={'class': 'form-control', 'placeholder': 'Enter at least 8 characters'})
    
    submit = SubmitField('Reset Password', render_kw={'class': 'btn btn-danger'})


# ── Document Management Forms ────────────────────────────────────────
from wtforms import HiddenField

class DocumentUploadForm(FlaskForm):
    title = StringField('Document Title', validators=[
        DataRequired(message='Document Title is required'),
        Length(max=255)
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g. FY 24-25 GSTR-1 September'})
    
    description = TextAreaField('Description', validators=[
        Optional()
    ], render_kw={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional context...'})
    
    document_type = SelectField('Document Type', choices=[
        ('Income Tax Return', 'Income Tax Return'),
        ('GST Return', 'GST Return'),
        ('Audit Report', 'Audit Report'),
        ('Balance Sheet', 'Balance Sheet'),
        ('Profit & Loss Statement', 'Profit & Loss Statement'),
        ('Bank Statement', 'Bank Statement'),
        ('Investment Report', 'Investment Report'),
        ('TDS Certificate', 'TDS Certificate'),
        ('Notice', 'Notice'),
        ('Invoice', 'Invoice'),
        ('Other', 'Other')
    ], render_kw={'class': 'form-select'})
    
    financial_year = SelectField('Financial Year', choices=[
        ('2023-24', '2023-24'),
        ('2024-25', '2024-25'),
        ('2025-26', '2025-26'),
        ('2026-27', '2026-27')
    ], default='2025-26', render_kw={'class': 'form-select'})
    
    cloudinary_url = HiddenField('Cloudinary URL', validators=[DataRequired(message="Please upload a document.")])
    cloudinary_public_id = HiddenField('Cloudinary Public ID', validators=[DataRequired()])
    original_filename = HiddenField('Original Filename', validators=[DataRequired()])
    file_size = HiddenField('File Size', validators=[DataRequired()])
    
    tags = StringField('Tags', validators=[
        Optional(),
        Length(max=500)
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g. Q1, Urgent, Draft (comma-separated)'})
    
    password_protected = BooleanField('Protect with Password', render_kw={'class': 'form-check-input'})
    
    pdf_password = PasswordField('PDF Access Password', validators=[
        Optional(),
        Length(min=4, message='Password must be at least 4 characters')
    ], render_kw={'class': 'form-control', 'placeholder': 'Keep blank to leave unprotected'})
    
    submit = SubmitField('Save Document', render_kw={'class': 'btn btn-primary'})


class DocumentEditForm(FlaskForm):
    title = StringField('Document Title', validators=[
        DataRequired(message='Document Title is required'),
        Length(max=255)
    ], render_kw={'class': 'form-control'})
    
    description = TextAreaField('Description', validators=[
        Optional()
    ], render_kw={'class': 'form-control', 'rows': 2})
    
    tags = StringField('Tags', validators=[
        Optional(),
        Length(max=500)
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g. Q1, Urgent, Draft (comma-separated)'})
    
    document_type = SelectField('Document Type', choices=[
        ('Income Tax Return', 'Income Tax Return'),
        ('GST Return', 'GST Return'),
        ('Audit Report', 'Audit Report'),
        ('Balance Sheet', 'Balance Sheet'),
        ('Profit & Loss Statement', 'Profit & Loss Statement'),
        ('Bank Statement', 'Bank Statement'),
        ('Investment Report', 'Investment Report'),
        ('TDS Certificate', 'TDS Certificate'),
        ('Notice', 'Notice'),
        ('Invoice', 'Invoice'),
        ('Other', 'Other')
    ], render_kw={'class': 'form-select'})
    
    financial_year = SelectField('Financial Year', choices=[
        ('2023-24', '2023-24'),
        ('2024-25', '2024-25'),
        ('2025-26', '2025-26'),
        ('2026-27', '2026-27')
    ], render_kw={'class': 'form-select'})
    
    password_protected = BooleanField('Protect with Password', render_kw={'class': 'form-check-input'})
    
    pdf_password = PasswordField('New Access Password', validators=[
        Optional(),
        Length(min=4, message='Password must be at least 4 characters')
    ], render_kw={'class': 'form-control', 'placeholder': 'Leave blank to keep existing password'})
    
    submit = SubmitField('Save Metadata', render_kw={'class': 'btn btn-primary'})


class DocumentReplaceForm(FlaskForm):
    cloudinary_url = HiddenField('Cloudinary URL', validators=[DataRequired(message="Please upload a document.")])
    cloudinary_public_id = HiddenField('Cloudinary Public ID', validators=[DataRequired()])
    original_filename = HiddenField('Original Filename', validators=[DataRequired()])
    file_size = HiddenField('File Size', validators=[DataRequired()])
    
    submit = SubmitField('Save Replacement', render_kw={'class': 'btn btn-primary'})


class BulkUploadForm(FlaskForm):
    # Store JSON array of uploaded file metadata
    uploaded_files_data = HiddenField('Uploaded Files Data', validators=[DataRequired(message="Please upload at least one document.")])
    
    submit = SubmitField('Process Uploads', render_kw={'class': 'btn btn-primary'})


class PasswordGatewayForm(FlaskForm):
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ], render_kw={'class': 'form-control', 'placeholder': 'Enter document password'})
    
    submit = SubmitField('Access Document', render_kw={'class': 'btn btn-primary'})

