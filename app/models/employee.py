from datetime import datetime, timezone
from ..extensions import db

class Employee(db.Model):
    """
    Employee profile linked to their User record.
    """
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                        unique=True, nullable=False, index=True)

    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    designation = db.Column(db.String(100), nullable=True)
    joining_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False) # Active / Inactive
    notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f'<Employee {self.full_name} (user_id={self.user_id})>'
