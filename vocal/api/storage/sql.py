from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        String, func as f, MetaData
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID
from sqlalchemy.schema import Table

metadata = MetaData()

contact_method_type = Enum('email', 'phone', 'address', name='contact_method_type',
                         create_type=False)
user_role = Enum('superuser', 'manager', 'creator', 'member', 'subscriber', name='user_role',
                create_type=False)

utcnow = f.timezone('UTC', f.now())

user_profile = Table('user_profile', metadata,
    Column('user_profile_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
    Column('display_name', String),
    Column('name', String, nullable=False),
    Column('created_at', DateTime, nullable=False, server_default=utcnow),
    Column('role', user_role, nullable=False, server_default='subscriber'))

user_auth = Table('user_auth', metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('password_crypt', String, nullable=False))

contact_method = Table('contact_method', metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('contact_method_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
    Column('contact_method_type', contact_method_type, nullable=False),
    Column('verified', Boolean, nullable=False))

email_contact_method = Table('email_contact_method', metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('contact_method_id', UUID, primary_key=True),
    Column('email_address', String, nullable=False),
    ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                         ['contact_method.user_profile_id', 'contact_method.contact_method_id']))

phone_contact_method = Table('phone_contact_method', metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('contact_method_id', UUID, primary_key=True),
    Column('phone_number', String, nullable=False),
    ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                         ['contact_method.user_profile_id', 'contact_method.contact_method_id']))

address_contact_method = Table('address_contact_method', metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
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
                         ['contact_method.user_profile_id', 'contact_method.contact_method_id']))
