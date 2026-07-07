"""
CA Manage — Database Seeder

Creates default admin, sample employee, and sample client for development.
Run: python seed.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.client import ClientProfile
from app.models.employee import Employee


def seed():
    """Seed the database with initial data."""
    app = create_app()

    with app.app_context():
        print('🌱 Seeding database...\n')

        # ── 1. Create Admin ─────────────────────────────────────────
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@camanage.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@123')
        admin_name = os.getenv('ADMIN_NAME', 'System Administrator')

        existing_admin = User.query.filter_by(email=admin_email).first()
        if existing_admin:
            print(f'  ⚠  Admin already exists: {admin_email}')
        else:
            admin = User(
                email=admin_email,
                full_name=admin_name,
                phone='+91-9999999999',
                role='admin',
                is_active=True,
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            print(f'  ✅ Admin created: {admin_email} / {admin_password}')

        # ── 2. Create Sample Employee ───────────────────────────────
        emp_email = 'employee@camanage.com'
        existing_emp = User.query.filter_by(email=emp_email).first()
        if existing_emp:
            print(f'  ⚠  Employee already exists: {emp_email}')
            # Make sure Employee profile exists
            if not existing_emp.employee_profile:
                employee_profile = Employee(
                    user_id=existing_emp.id,
                    full_name='Rahul Sharma',
                    email=existing_emp.email,
                    phone='+91-9876543210',
                    designation='Senior Associate',
                    notes='Development employee profile.',
                    status='Active'
                )
                db.session.add(employee_profile)
                print('     Profile: Created missing employee profile record.')
        else:
            employee = User(
                email=emp_email,
                full_name='Rahul Sharma',
                phone='+91-9876543210',
                role='employee',
                is_active=True,
            )
            employee.set_password('Employee@123')
            db.session.add(employee)
            db.session.flush()

            # Create employee profile
            employee_profile = Employee(
                user_id=employee.id,
                full_name=employee.full_name,
                email=employee.email,
                phone=employee.phone,
                designation='Senior Associate',
                notes='Development employee profile.',
                status='Active'
            )
            db.session.add(employee_profile)
            print(f'  ✅ Employee created: {emp_email} / Employee@123')

        # ── 3. Create Sample Client ─────────────────────────────────
        client_email = 'client@camanage.com'
        existing_client = User.query.filter_by(email=client_email).first()
        if existing_client:
            print(f'  ⚠  Client already exists: {client_email}')
        else:
            client_user = User(
                email=client_email,
                full_name='Priya Patel',
                phone='+91-9988776655',
                role='client',
                is_active=True,
            )
            client_user.set_password('Client@123')
            db.session.add(client_user)
            db.session.flush()  # Get the ID before creating profile

            # Create client profile
            profile = ClientProfile(
                user_id=client_user.id,
                full_name=client_user.full_name,
                email=client_user.email,
                phone=client_user.phone,
                firm_name='Patel Trading Co.',
                PAN='ABCDE1234F',
                GST='27ABCDE1234F1Z5',
                client_type='business',
                address='123 MG Road',
                city='Mumbai',
                state='Maharashtra',
                pincode='400001',
                notes='Sample client for development testing.',
                status='Active'
            )

            # Assign to employee if exists
            emp = User.query.filter_by(email=emp_email).first()
            if emp:
                profile.assigned_employee_id = emp.id

            db.session.add(profile)
            print(f'  ✅ Client created: {client_email} / Client@123')
            print(f'     Profile: {profile.firm_name} (PAN: {profile.PAN})')

        # ── Commit ──────────────────────────────────────────────────
        db.session.commit()
        print('\n✨ Seeding complete!')
        print('\n── Login Credentials ──────────────────────')
        print(f'  Admin:    {admin_email} / {admin_password}')
        print(f'  Employee: {emp_email} / Employee@123')
        print(f'  Client:   {client_email} / Client@123')
        print('───────────────────────────────────────────\n')


if __name__ == '__main__':
    seed()
