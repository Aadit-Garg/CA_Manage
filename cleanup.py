"""
CA Manage — Database & Cloudinary Cleanup Script

Wipes ALL data from the Neon database and ALL files from Cloudinary,
then re-seeds the admin account so you can log in again.

Run: python cleanup.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User

import cloudinary
import cloudinary.api


def cleanup():
    app = create_app()

    with app.app_context():
        print('🧹 CA Manage — Full Cleanup')
        print('=' * 50)

        # ── 1. Wipe Cloudinary ──────────────────────────────────
        print('\n📦 Cleaning Cloudinary storage...')
        try:
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                api_key=os.getenv('CLOUDINARY_API_KEY'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET'),
                secure=True
            )

            # Delete all raw resources in the ca_manage_docs folder
            deleted_count = 0
            try:
                result = cloudinary.api.resources(
                    type='upload',
                    resource_type='raw',
                    prefix='ca_manage_docs/',
                    max_results=500
                )
                resources = result.get('resources', [])
                if resources:
                    public_ids = [r['public_id'] for r in resources]
                    # Cloudinary batch delete (max 100 at a time)
                    for i in range(0, len(public_ids), 100):
                        batch = public_ids[i:i+100]
                        cloudinary.api.delete_resources(batch, resource_type='raw')
                        deleted_count += len(batch)
                    print(f'  ✅ Deleted {deleted_count} files from Cloudinary')
                else:
                    print('  ℹ  No files found in Cloudinary ca_manage_docs/')
            except cloudinary.exceptions.NotFound:
                print('  ℹ  No ca_manage_docs folder found in Cloudinary')
            except Exception as e:
                print(f'  ⚠  Cloudinary folder cleanup error: {e}')

            # Also try to delete any image resources (icons, etc.) if any
            try:
                result = cloudinary.api.resources(
                    type='upload',
                    resource_type='image',
                    prefix='ca_manage_docs/',
                    max_results=500
                )
                resources = result.get('resources', [])
                if resources:
                    public_ids = [r['public_id'] for r in resources]
                    for i in range(0, len(public_ids), 100):
                        batch = public_ids[i:i+100]
                        cloudinary.api.delete_resources(batch, resource_type='image')
                    print(f'  ✅ Deleted {len(resources)} image resources')
            except Exception:
                pass  # No image resources, that's fine

        except Exception as e:
            print(f'  ❌ Cloudinary cleanup failed: {e}')

        # ── 2. Wipe Database ────────────────────────────────────
        print('\n🗄️  Cleaning Neon database...')

        # Delete in correct order to respect foreign key constraints
        tables_in_order = [
            'upload_session_files',
            'upload_sessions',
            'push_subscriptions',
            'notifications',
            'timeline_events',
            'audit_logs',
            'saved_filters',
            'approval_requests',
            'document_versions',
            'documents',
            'attendance',
            'employees',
            'client_profiles',
            'users',
        ]

        for table in tables_in_order:
            try:
                result = db.session.execute(db.text(f'DELETE FROM {table}'))
                count = result.rowcount
                if count > 0:
                    print(f'  🗑  {table}: deleted {count} rows')
                else:
                    print(f'  ·  {table}: already empty')
            except Exception as e:
                print(f'  ⚠  {table}: {e}')
                db.session.rollback()

        db.session.commit()
        print('\n  ✅ All database tables cleared')

        # ── 3. Re-seed Admin ────────────────────────────────────
        print('\n🌱 Re-creating admin account...')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@camanage.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@123')
        admin_name = os.getenv('ADMIN_NAME', 'System Administrator')

        admin = User(
            email=admin_email,
            full_name=admin_name,
            phone='+91-9999999999',
            role='admin',
            is_active=True,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

        print(f'  ✅ Admin created: {admin_email} / {admin_password}')

        # ── Done ────────────────────────────────────────────────
        print('\n' + '=' * 50)
        print('✨ Cleanup complete! Fresh start.')
        print(f'\n  Login: {admin_email} / {admin_password}')
        print()


if __name__ == '__main__':
    # Safety confirmation
    print('\n⚠️  WARNING: This will DELETE ALL DATA from:')
    print('   • Neon PostgreSQL database (all tables)')
    print('   • Cloudinary storage (all uploaded PDFs)')
    print('\n   Only the admin account will be re-created.\n')

    confirm = input('Type "yes" to proceed: ').strip().lower()
    if confirm != 'yes':
        print('Aborted.')
        sys.exit(0)

    cleanup()
