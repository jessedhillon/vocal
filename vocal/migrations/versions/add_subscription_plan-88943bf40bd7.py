"""add subscription plan

Revision ID: 88943bf40bd7
Revises: aa4168fa63a9
Create Date: 2020-11-25 20:09:50.401529

"""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        Numeric, String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID
from sqlalchemy.sql import column, or_, null


import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = '88943bf40bd7'
down_revision = 'aa4168fa63a9'
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())

subscription_plan_status = Enum('active', 'inactive', name='subscription_plan_status',
                                create_type=False)
payment_demand_type = Enum('periodic', 'immediate', 'pay-go', name='payment_demand_type',
                           create_type=False)
payment_demand_period = Enum('daily', 'weekly', 'monthly', 'quarterly', 'annually',
                             name='payment_demand_period', create_type=False)


def upgrade():
    subscription_plan_status.create(op.get_bind())
    payment_demand_type.create(op.get_bind())
    payment_demand_period.create(op.get_bind())

    op.create_table(
        'subscription_plan',
        Column('subscription_plan_id', UUID, primary_key=True,
               server_default=f.gen_random_uuid()),
        Column('status', subscription_plan_status, nullable=False, server_default='active'),
        Column('rank', Integer),
        Column('name', String),
        Column('description', String, nullable=False))

    op.create_table(
        'payment_demand',
        Column('subscription_plan_id', UUID, ForeignKey('subscription_plan.subscription_plan_id'),
               primary_key=True),
        Column('payment_demand_id', UUID, primary_key=True, server_default=f.gen_random_uuid()),
        Column('demand_type', payment_demand_type, nullable=False))

    op.create_table(
        'periodic_payment_demand',
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
    op.create_unique_constraint(
        'uq_periodic_payment_demand_currency',
        'periodic_payment_demand',
        ['subscription_plan_id', 'payment_demand_id', 'period', 'iso_currency',
            'non_iso_currency'])
    op.create_check_constraint(
        'ck_periodic_payment_demand_currency',
        'periodic_payment_demand',
        (column('iso_currency').is_(None)) | (column('non_iso_currency').is_(None)))

    op.create_table(
        'immediate_payment_demand',
        Column('subscription_plan_id', UUID, ForeignKey('subscription_plan.subscription_plan_id'),
               primary_key=True),
        Column('payment_demand_id', UUID, primary_key=True),
        Column('iso_currency', String(3)),
        Column('non_iso_currency', String),
        Column('amount', Numeric(20, 6), nullable=False),
        ForeignKeyConstraint(['subscription_plan_id', 'payment_demand_id'],
                             ['payment_demand.subscription_plan_id',
                              'payment_demand.payment_demand_id']))
    op.create_unique_constraint(
        'uq_immediate_payment_demand_currency',
        'immediate_payment_demand',
        ['subscription_plan_id', 'payment_demand_id', 'iso_currency', 'non_iso_currency'])
    op.create_check_constraint(
        'ck_immediate_payment_demand_currency',
        'immediate_payment_demand',
        (column('iso_currency').is_(None)) | (column('non_iso_currency').is_(None)))


def downgrade():
    op.drop_table('immediate_payment_demand')
    op.drop_table('periodic_payment_demand')
    op.drop_table('payment_demand')
    op.drop_table('subscription_plan')

    subscription_plan_status.drop(op.get_bind())
    payment_demand_type.drop(op.get_bind())
    payment_demand_period.drop(op.get_bind())
