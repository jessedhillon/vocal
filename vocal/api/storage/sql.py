from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        Numeric, String, func as f, MetaData
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID
from sqlalchemy.schema import Table

metadata = MetaData()

contact_method_type = Enum('email', 'phone', 'address', name='contact_method_type',
                           create_type=False)
user_role = Enum('superuser', 'manager', 'creator', 'member', 'subscriber', name='user_role',
                 create_type=False)
subscription_plan_status = Enum('active', 'inactive', name='subscription_plan_status',
                                create_type=False)
payment_demand_type = Enum('periodic', 'immediate', 'pay-go', name='payment_demand_type',
                           create_type=False)
payment_demand_period = Enum('daily', 'weekly', 'monthly', 'quarterly', 'annually',
                             name='payment_demand_period', create_type=False)
utcnow = f.timezone('UTC', f.now())

user_profile = Table(
    'user_profile',
    metadata,
    Column('user_profile_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
    Column('display_name', String),
    Column('name', String, nullable=False),
    Column('created_at', DateTime, nullable=False, server_default=utcnow),
    Column('role', user_role, nullable=False, server_default='subscriber'))

user_auth = Table(
    'user_auth',
    metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('password_crypt', String, nullable=False))

contact_method = Table(
    'contact_method',
    metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('contact_method_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
    Column('contact_method_type', contact_method_type, nullable=False),
    Column('verified', Boolean, nullable=False))

email_contact_method = Table(
    'email_contact_method',
    metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('contact_method_id', UUID, primary_key=True),
    Column('email_address', String, nullable=False),
    ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                         ['contact_method.user_profile_id', 'contact_method.contact_method_id']))

phone_contact_method = Table(
    'phone_contact_method',
    metadata,
    Column('user_profile_id', UUID, ForeignKey('user_profile.user_profile_id'), primary_key=True),
    Column('contact_method_id', UUID, primary_key=True),
    Column('phone_number', String, nullable=False),
    ForeignKeyConstraint(['user_profile_id', 'contact_method_id'],
                         ['contact_method.user_profile_id', 'contact_method.contact_method_id']))

address_contact_method = Table(
    'address_contact_method',
    metadata,
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

subscription_plan = Table(
    'subscription_plan',
    metadata,
    Column('subscription_plan_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
    Column('status', subscription_plan_status, nullable=False, server_default='active'),
    Column('rank', Integer),
    Column('name', String),
    Column('description', String, nullable=False))

payment_demand = Table(
    'payment_demand',
    metadata,
    Column('subscription_plan_id', UUID, ForeignKey('subscription_plan.subscription_plan_id'),
           primary_key=True),
    Column('payment_demand_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
    Column('demand_type', payment_demand_type, nullable=False))

periodic_payment_demand = Table(
    'periodic_payment_demand',
    metadata,
    Column('subscription_plan_id', UUID, ForeignKey('subscription_plan.subscription_plan_id'),
           primary_key=True),
    Column('payment_demand_id', UUID, primary_key=True),
    Column('period', payment_demand_period, nullable=False),
    Column('iso_currency', String(3)),
    Column('non_iso_currency', String),
    Column('amount', Numeric(20, 6), nullable=False),
    ForeignKeyConstraint(['subscription_plan_id', 'payment_demand_id'],
                         ['payment_demand.subscription_plan_id',
                          'payment_demand.payment_demand_id']))

immediate_payment_demand = Table(
    'immediate_payment_demand',
    metadata,
    Column('subscription_plan_id', UUID, ForeignKey('subscription_plan.subscription_plan_id'),
           primary_key=True),
    Column('payment_demand_id', UUID, primary_key=True),
    Column('iso_currency', String(3)),
    Column('non_iso_currency', String),
    Column('amount', Numeric(20, 6), nullable=False),
    ForeignKeyConstraint(['subscription_plan_id', 'payment_demand_id'],
                         ['payment_demand.subscription_plan_id',
                          'payment_demand.payment_demand_id']))
