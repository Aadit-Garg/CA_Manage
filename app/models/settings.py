from app.extensions import db
from datetime import datetime

class FirmSettings(db.Model):
    __tablename__ = 'firm_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_name = db.Column(db.String(255), default="Sumit N Garg & Associates")
    logo_url = db.Column(db.String(500), default="/static/img/logo.png")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings
