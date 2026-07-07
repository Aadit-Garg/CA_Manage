from datetime import datetime, timezone
from ..extensions import db

class Attendance(db.Model):
    """
    Tracks daily employee attendance, including geolocation for remote/mobile punch-ins.
    """
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Core Attendance Data
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date(), index=True)
    punch_in_time = db.Column(db.DateTime, nullable=True)
    punch_out_time = db.Column(db.DateTime, nullable=True)
    total_hours = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), nullable=False, default='Present') # Present, Half Day, Absent, Leave, Holiday, Corrected
    
    # Location and Device Data
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    gps_accuracy = db.Column(db.Float, nullable=True) # in meters
    location_status = db.Column(db.String(50), nullable=True) # Captured, Denied, Unavailable
    device_info = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    
    # Admin modifications and audit
    notes = db.Column(db.Text, nullable=True)
    corrected_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('attendance_records', lazy=True, cascade='all, delete-orphan'))
    corrected_by = db.relationship('User', foreign_keys=[corrected_by_id])

    def __repr__(self):
        return f'<Attendance {self.employee_id} on {self.date} - {self.status}>'
