"""initial commit

Revision ID: 221c3b472f5c
Revises:
Create Date: 2020-11-17 10:41:26.931244

"""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID

import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = '221c3b472f5c'
down_revision = None
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())

contact_method_type = Enum('email', 'phone', 'address', name='contact_method_type',
                           create_type=False)


def upgrade():
    op.create_extension('pgcrypto')

    contact_method_type.create(op.get_bind())

    op.create_table(
        'user_profile',
        Column('user_profile_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
        Column('display_name', String),
        Column('name', String, nullable=False),
        Column('created_at', DateTime, nullable=False, server_default=utcnow))

    op.create_table(
        'user_auth',
        Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'),
               primary_key=True),
        Column('password_crypt', String, nullable=False))

    op.create_table(
        'contact_method',
        Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'),
               primary_key=True),
        Column('contact_method_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
        Column('contact_method_type', contact_method_type, nullable=False),
        Column('verified', Boolean, nullable=False))

    op.create_table(
        'email_contact_method',
        Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'),
               primary_key=True),
        Column('contact_method_id', UUID, primary_key=True),
        Column('email_address', String, nullable=False),
        ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                             ['contact_method.user_profile_id',
                              'contact_method.contact_method_id']))

    op.create_table(
        'phone_contact_method',
        Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'),
               primary_key=True),
        Column('contact_method_id', UUID, primary_key=True),
        Column('phone_number', String, nullable=False),
        ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                             ['contact_method.user_profile_id',
                              'contact_method.contact_method_id']))

    op.create_table(
        'address_contact_method',
        Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'),
               primary_key=True),
        Column('contact_method_id', UUID, primary_key=True),
        Column('country_code', String(2), nullable=False),
        Column('administrative_area', String, nullable=False),
        Column('locality', String, nullable=False),
        Column('depdendent_locality', String, nullable=False),
        Column('postal_code', String, nullable=False),
        Column('sorting_code', String, nullable=False),
        Column('address_2', String, nullable=False),
        Column('address_1', String, nullable=False),
        Column('organization', String, nullable=False),
        Column('name', String, nullable=False),
        ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                             ['contact_method.user_profile_id',
                              'contact_method.contact_method_id']))


def downgrade():
    op.drop_table('address_contact_method')
    op.drop_table('email_contact_method')
    op.drop_table('phone_contact_method')
    op.drop_table('contact_method')
    op.drop_table('user_auth')
    op.drop_table('user_profile')

    contact_method_type.drop(op.get_bind())

    op.drop_extension('pgcrypto')
