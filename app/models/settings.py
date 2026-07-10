from app.extensions import db
from datetime import datetime

class FirmSettings(db.Model):
    __tablename__ = 'firm_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_name = db.Column(db.String(255), default="Sumit N Garg & Associates")
    firm_address = db.Column(db.Text, nullable=True)
    gstin = db.Column(db.String(50), nullable=True)
    logo_url = db.Column(db.String(500), default="/static/img/logo.png")
    
    # Invoice Defaults
    bank_account_name = db.Column(db.String(255), nullable=True)
    bank_name = db.Column(db.String(255), nullable=True)
    account_number = db.Column(db.String(100), nullable=True)
    ifsc_code = db.Column(db.String(50), nullable=True)
    default_notes = db.Column(db.Text, nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings
