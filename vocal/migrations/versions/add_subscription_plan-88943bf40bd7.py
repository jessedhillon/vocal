"""add subscription plan

Revision ID: 88943bf40bd7
Revises: aa4168fa63a9
Create Date: 2020-11-25 20:09:50.401529

"""
from functools import partial

from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        Numeric, String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID
from sqlalchemy.sql import column, or_, null

from vocal.constants import ISO4217Currency
import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = '88943bf40bd7'
down_revision = 'aa4168fa63a9'
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())
v4_uuid = f.gen_random_uuid()

Enum = partial(Enum, values_callable=lambda en: [e.value for e in en], create_type=False)
subscription_plan_status = Enum('active', 'inactive', name='subscription_plan_status',
                                create_type=False)
payment_demand_type = Enum('periodic', 'immediate', 'pay-go', name='payment_demand_type',
                           create_type=False)
payment_demand_period = Enum('daily', 'weekly', 'monthly', 'quarterly', 'annually',
                             name='payment_demand_period', create_type=False)
payment_demand_status = Enum('active', 'inactive', name='payment_demand_status',
                             create_type=False)
iso_4217_currency = Enum(ISO4217Currency, name='iso_4217_currency')


def upgrade():
    subscription_plan_status.create(op.get_bind())
    payment_demand_type.create(op.get_bind())
    payment_demand_period.create(op.get_bind())
    payment_demand_status.create(op.get_bind())
    iso_4217_currency.create(op.get_bind())

    op.create_table(
        'subscription_plan',
        Column('subscription_plan_id', UUID, primary_key=True, server_default=v4_uuid),
        Column('status', subscription_plan_status, nullable=False, server_default='active'),
        Column('rank', Integer),
        Column('name', String),
        Column('description', String, nullable=False))

    op.create_table(
        'payment_demand',
        Column('subscription_plan_id', UUID, ForeignKey('subscription_plan.subscription_plan_id'),
               primary_key=True),
        Column('payment_demand_id', UUID, primary_key=True, server_default=v4_uuid),
        Column('status', payment_demand_status, server_default='active'),
        Column('demand_type', payment_demand_type, nullable=False),
        Column('period', payment_demand_period),
        Column('iso_currency', String(3)),
        Column('non_iso_currency', String),
        Column('amount', Numeric(20, 6), nullable=False))
    op.create_check_constraint(
        'ck_payment_demand_currency',
        'payment_demand',
        (column('iso_currency').is_not(None) & column('non_iso_currency').is_(None)) |
        (column('iso_currency').is_(None) & column('non_iso_currency').is_not(None)))
    op.create_check_constraint(
        'ck_payment_demand_periodic_type',
        'payment_demand',
        ((column('demand_type') == 'periodic') & (column('period').is_not(None))) |
        ((column('demand_type') == 'immediate') & (column('period').is_(None))))
    op.execute("""CREATE UNIQUE INDEX uq_active_payment_demand
                  ON payment_demand (subscription_plan_id, payment_demand_id,
                                     demand_type, period, iso_currency, non_iso_currency)
                  WHERE (status = 'active')""")


def downgrade():
    op.drop_table('payment_demand')
    op.drop_table('subscription_plan')

    subscription_plan_status.drop(op.get_bind())
    payment_demand_type.drop(op.get_bind())
    payment_demand_period.drop(op.get_bind())
    payment_demand_status.drop(op.get_bind())
    iso_4217_currency.drop(op.get_bind())
