from app import db
from datetime import datetime

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client_profiles.id', ondelete='SET NULL'), nullable=True)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Draft') # Draft, Pending, Paid, Overdue
    
    # Client Snapshot
    client_name = db.Column(db.String(150))
    client_address = db.Column(db.Text)
    client_gstin = db.Column(db.String(50))
    client_pan = db.Column(db.String(50))
    
    # Firm Settings Overrides (if null, fall back to global settings)
    firm_name = db.Column(db.String(150))
    firm_address = db.Column(db.Text)
    bank_account_name = db.Column(db.String(150))
    bank_name = db.Column(db.String(150))
    account_number = db.Column(db.String(50))
    ifsc_code = db.Column(db.String(20))
    
    # Tax configuration
    tax_type = db.Column(db.String(10), default='IGST') # 'IGST' or 'CGST_SGST'
    igst_rate = db.Column(db.Float, default=18.0)
    cgst_rate = db.Column(db.Float, default=9.0)
    sgst_rate = db.Column(db.Float, default=9.0)
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    client = db.relationship('ClientProfile', backref='invoices')
    items = db.relationship('InvoiceItem', backref='invoice', cascade="all, delete-orphan", lazy=True)
    
    @property
    def subtotal(self):
        return sum(item.amount for item in self.items)
        
    @property
    def total_tax(self):
        if self.tax_type == 'IGST':
            return self.subtotal * (self.igst_rate / 100)
        else:
            return self.subtotal * ((self.cgst_rate + self.sgst_rate) / 100)
            
    @property
    def total_amount(self):
        return self.subtotal + self.total_tax


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    sac_code = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
