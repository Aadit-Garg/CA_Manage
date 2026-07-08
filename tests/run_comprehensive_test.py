import unittest
import io
import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.client import ClientProfile
from app.models.employee import Employee
from werkzeug.security import generate_password_hash
from app.utils.import_helper import generate_excel_template
from openpyxl import load_workbook

class CAManageComprehensiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        db.create_all()
        
        # Setup test users
        cls.admin_email = "test_runner_admin@camanage.com"
        cls.employee_email = "test_runner_emp@camanage.com"
        cls.client_email = "test_runner_client@camanage.com"
        

        
        # Create Admin
        admin = User(email=cls.admin_email, password_hash=generate_password_hash("password"), role='admin', full_name="Admin User")
        db.session.add(admin)
        
        # Create Employee
        emp_user = User(email=cls.employee_email, password_hash=generate_password_hash("password"), role='employee', full_name="Employee User")
        db.session.add(emp_user)
        db.session.flush()
        emp = Employee(user_id=emp_user.id, full_name="Test Employee", email=cls.employee_email, phone="123")
        db.session.add(emp)
        
        # Create Client
        client_user = User(email=cls.client_email, password_hash=generate_password_hash("password"), role='client', full_name="Client User")
        db.session.add(client_user)
        db.session.flush()
        c = ClientProfile(user_id=client_user.id, full_name="Test Client", client_code="CLI-TEST", email=cls.client_email)
        db.session.add(c)
        
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.drop_all()
        cls.app_context.pop()

    def login(self, email, password='password'):
        res = self.client.post('/auth/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)
        if b"Invalid" in res.data or b"Please log in" in res.data:
            print("Login failed for", email)
            print(res.data)
        return res

    def logout(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    def test_01_pwa_metadata(self):
        """Test PWA Manifest and Service Worker routes"""
        res = self.client.get('/manifest.json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/manifest+json')
        
        res = self.client.get('/sw.js')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/javascript')

    def test_02_rbac_smoke(self):
        """Test that unauthenticated users cannot access protected routes"""
        self.logout()
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 302) # Redirects to login
        
        res = self.client.get('/employee/dashboard')
        self.assertEqual(res.status_code, 302)

    def test_03_admin_routes(self):
        """Test admin role can access admin routes"""
        self.login(self.admin_email)
        routes_to_test = [
            '/admin/dashboard',
            '/admin/clients',
            '/admin/employees',
            '/admin/documents',
            '/admin/clients/import'
        ]
        for route in routes_to_test:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route failed: {route}")
            
    def test_04_download_import_template(self):
        """Test the bulk import template generation and download"""
        self.login(self.admin_email)
        res = self.client.get('/admin/clients/import-template')
        self.assertEqual(res.status_code, 200)
        self.assertTrue('spreadsheetml' in res.mimetype)

    def test_05_bulk_upload_validation(self):
        """Test the bulk upload validation logic by simulating an upload"""
        self.login(self.admin_email)
        
        # Get template
        stream = generate_excel_template()
        wb = load_workbook(stream)
        ws = wb["Clients Template"]
        
        # Add a valid row
        ws.append(["Bulk Test Name", "bulk_test@camanage.com", "9999999999", "Address", "City", "State", "123", "ABCDE1234F", "27ABCDE1234F1Z5", "Notes"])
        
        # Save to bytes
        new_stream = io.BytesIO()
        wb.save(new_stream)
        new_stream.seek(0)
        
        # Post the file
        data = {'file': (new_stream, 'test_upload.xlsx')}
        res = self.client.post('/admin/clients/import', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Bulk Test Name", res.data)
        self.assertIn(b"Ready to Import", res.data) # Check valid rows exist

if __name__ == '__main__':
    unittest.main(verbosity=2)
