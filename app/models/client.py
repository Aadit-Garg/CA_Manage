from datetime import datetime, timezone
from ..extensions import db

class ClientProfile(db.Model):
    """
    One-to-one extension of User for client-specific data.
    """
    __tablename__ = 'client_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                        unique=True, nullable=False, index=True)

    client_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    upload_id = db.Column(db.String(20), unique=True, nullable=True, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)

    # Address
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)

    # Tax Details
    PAN = db.Column(db.String(10), unique=True, nullable=True, index=True)
    GST = db.Column(db.String(15), unique=True, nullable=True, index=True)

    # Management
    assigned_employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False) # Active / Inactive

    # Business details (for backwards compatibility/extra context if needed)
    firm_name = db.Column(db.String(200), nullable=True)
    client_type = db.Column(db.String(20), default='individual', nullable=False) # individual / business

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    TYPE_INDIVIDUAL = 'individual'
    TYPE_BUSINESS = 'business'
    VALID_TYPES = (TYPE_INDIVIDUAL, TYPE_BUSINESS)

    @property
    def display_name(self):
        """Show firm name if business, otherwise the client's full name."""
        if self.client_type == self.TYPE_BUSINESS and self.firm_name:
            return self.firm_name
        return self.full_name

    @property
    def masked_pan(self):
        """Return masked PAN for display (e.g., ABCDE****F)."""
        if self.PAN and len(self.PAN) == 10:
            return self.PAN[:5] + '****' + self.PAN[9:]
        return self.PAN or '—'

    def __repr__(self):
        return f'<ClientProfile {self.display_name} ({self.client_code})>'


def generate_upload_id(connection):
    import random
    import string
    
    while True:
        # Generate format CLI-XXXXXX
        chars = string.ascii_uppercase + string.digits
        suffix = ''.join(random.choices(chars, k=6))
        uid = f"CLI-{suffix}"
        
        # Check if unique
        res = connection.execute(
            db.text("SELECT id FROM client_profiles WHERE upload_id = :uid"),
            {"uid": uid}
        ).fetchone()
        
        if not res:
            return uid

# ── Auto-generate Client Code and Upload ID ────────────────────────
@db.event.listens_for(ClientProfile, 'before_insert')
def receive_before_insert(mapper, connection, target):
    if not target.client_code:
        # Fetch the max client_code from the DB using raw connection to avoid session issues
        result = connection.execute(
            db.text("SELECT client_code FROM client_profiles WHERE client_code IS NOT NULL")
        ).fetchall()
        
        # Parse client codes, e.g. CL0001, CL0002
        codes = []
        for row in result:
            code_str = row[0]
            if code_str.startswith('CL'):
                try:
                    num = int(code_str[2:])
                    codes.append(num)
                except ValueError:
                    continue
        
        next_num = max(codes) + 1 if codes else 1
        target.client_code = f"CL{next_num:04d}"
        
    if not target.upload_id:
        target.upload_id = generate_upload_id(connection)
