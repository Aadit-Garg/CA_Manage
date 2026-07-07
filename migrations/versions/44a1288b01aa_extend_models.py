"""extend models

Revision ID: 44a1288b01aa
Revises: 6221ab1338b0
Create Date: 2026-07-08 00:41:44.611725

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '44a1288b01aa'
down_revision = '6221ab1338b0'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create employees table
    op.create_table('employees',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('designation', sa.String(length=100), nullable=True),
    sa.Column('joining_date', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_employees_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_employees_user_id'), ['user_id'], unique=True)

    # 2. Add client_profiles columns as nullable first
    op.add_column('client_profiles', sa.Column('client_code', sa.String(length=20), nullable=True))
    op.add_column('client_profiles', sa.Column('full_name', sa.String(length=150), nullable=True))
    op.add_column('client_profiles', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('client_profiles', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('client_profiles', sa.Column('PAN', sa.String(length=10), nullable=True))
    op.add_column('client_profiles', sa.Column('GST', sa.String(length=15), nullable=True))
    op.add_column('client_profiles', sa.Column('status', sa.String(length=20), nullable=True, server_default='Active'))

    # 3. Migrate existing data from users and old columns
    bind = op.get_bind()
    
    # Copy full_name, email, phone from users
    bind.execute(sa.text(
        "UPDATE client_profiles cp "
        "SET full_name = u.full_name, email = u.email, phone = u.phone "
        "FROM users u WHERE cp.user_id = u.id"
    ))
    
    # Copy pan_number and gst_number
    bind.execute(sa.text(
        "UPDATE client_profiles SET \"PAN\" = pan_number, \"GST\" = gst_number"
    ))
    
    # Assign client codes sequentially
    bind.execute(sa.text(
        "WITH numbered AS ( "
        "  SELECT id, ROW_NUMBER() OVER (ORDER BY id) as rn FROM client_profiles "
        ") "
        "UPDATE client_profiles cp "
        "SET client_code = 'CL' || lpad(n.rn::text, 4, '0') "
        "FROM numbered n WHERE cp.id = n.id"
    ))

    # Fill default status if missing
    bind.execute(sa.text(
        "UPDATE client_profiles SET status = 'Active' WHERE status IS NULL"
    ))

    # 4. Alter columns to NOT NULL now that data is populated
    op.alter_column('client_profiles', 'client_code', nullable=False)
    op.alter_column('client_profiles', 'full_name', nullable=False)
    op.alter_column('client_profiles', 'email', nullable=False)
    op.alter_column('client_profiles', 'status', nullable=False)

    # 5. Create indexes and drop old columns
    with op.batch_alter_table('client_profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_client_profiles_gst_number'))
        batch_op.drop_index(batch_op.f('ix_client_profiles_pan_number'))
        batch_op.create_index(batch_op.f('ix_client_profiles_GST'), ['GST'], unique=True)
        batch_op.create_index(batch_op.f('ix_client_profiles_PAN'), ['PAN'], unique=True)
        batch_op.create_index(batch_op.f('ix_client_profiles_client_code'), ['client_code'], unique=True)
        batch_op.create_index(batch_op.f('ix_client_profiles_email'), ['email'], unique=True)
        batch_op.drop_column('pan_number')
        batch_op.drop_column('gst_number')

    # 6. Alter users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('password_changed_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('password_changed_at')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('profile_picture')

    with op.batch_alter_table('client_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gst_number', sa.VARCHAR(length=15), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('pan_number', sa.VARCHAR(length=10), autoincrement=False, nullable=True))
        batch_op.drop_index(batch_op.f('ix_client_profiles_email'))
        batch_op.drop_index(batch_op.f('ix_client_profiles_client_code'))
        batch_op.drop_index(batch_op.f('ix_client_profiles_PAN'))
        batch_op.drop_index(batch_op.f('ix_client_profiles_GST'))
        batch_op.create_index('ix_client_profiles_pan_number', ['pan_number'], unique=False)
        batch_op.create_index('ix_client_profiles_gst_number', ['gst_number'], unique=False)
        batch_op.drop_column('status')
        batch_op.drop_column('GST')
        batch_op.drop_column('PAN')
        batch_op.drop_column('phone')
        batch_op.drop_column('email')
        batch_op.drop_column('full_name')
        batch_op.drop_column('client_code')

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_employees_user_id'))
        batch_op.drop_index(batch_op.f('ix_employees_email'))

    op.drop_table('employees')
