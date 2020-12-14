"""add subscription model

Revision ID: af4e234a4299
Revises: 88943bf40bd7
Create Date: 2020-12-07 07:30:50.509741

"""
from functools import partial

from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        Numeric, String, func as f, literal
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID

from vocal.constants import ISO4217Currency
import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = 'af4e234a4299'
down_revision = '88943bf40bd7'
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())
v4_uuid = f.gen_random_uuid()

Enum = partial(Enum, values_callable=lambda en: [e.value for e in en], create_type=False)
subscription_status = Enum('current', 'paused', 'expired', 'cancelled',
                           name='subscription_status', create_type=False)
payment_method_type = Enum('credit_card', 'cryptocurrency', 'eft', 'manual',
                           name='payment_method_type', create_type=False)
payment_method_status = Enum('current', 'expired', 'invalid',
                             name='payment_method_status', create_type=False)
iso_4217_currency = Enum(ISO4217Currency, name='iso_4217_currency')


def upgrade():
    subscription_status.create(op.get_bind())
    payment_method_type.create(op.get_bind())
    payment_method_status.create(op.get_bind())
    iso_4217_currency.create(op.get_bind())

    op.create_table(
        'payment_profile',
        Column('user_profile_id', UUID,
               ForeignKey('user_profile.user_profile_id'), primary_key=True),
        Column('payment_profile_id', UUID, primary_key=True, server_default=v4_uuid),
        Column('processor_id', String, nullable=False),
        Column('processor_customer_profile_id', String))
    op.create_unique_constraint('uq_payment_profile_processor', 'payment_profile',
                                ['user_profile_id', 'processor_id'])

    op.create_table(
        'payment_method',
        Column('user_profile_id', UUID,
               ForeignKey('user_profile.user_profile_id'), primary_key=True),
        Column('payment_profile_id', UUID, primary_key=True, server_default=v4_uuid),
        Column('payment_method_id', UUID, primary_key=True, server_default=v4_uuid),
        Column('processor_payment_method_id', String),
        Column('payment_method_type', payment_method_type),
        Column('payment_method_family', String),
        Column('display_name', String),
        Column('safe_account_number_fragment', String),
        Column('status', payment_method_status, nullable=False, server_default=literal('current')),
        Column('expires_after', DateTime),
        ForeignKeyConstraint(['user_profile_id', 'payment_profile_id'],
                             ['payment_profile.user_profile_id',
                              'payment_profile.payment_profile_id']))

    op.create_table(
        'payment_transaction',
        Column('transaction_id', Integer, primary_key=True, autoincrement=True),
        Column('user_profile_id', UUID,
               ForeignKey('user_profile.user_profile_id'), nullable=False),
        Column('payment_profile_id', UUID, nullable=True),
        Column('payment_method_id', UUID, nullable=True),
        Column('transacted_at', DateTime, nullable=False, server_default=utcnow),
        Column('success', Boolean, nullable=False),
        Column('processor_transaction_id', String),
        Column('amount', Numeric(20, 6), nullable=False),
        Column('iso_currency', iso_4217_currency),
        Column('non_iso_currency', String),
        Column('processor_response_raw', JSONB),
        ForeignKeyConstraint(['user_profile_id', 'payment_profile_id'],
                             ['payment_profile.user_profile_id',
                              'payment_profile.payment_profile_id']),
        ForeignKeyConstraint(['user_profile_id', 'payment_profile_id', 'payment_method_id'],
                             ['payment_method.user_profile_id',
                              'payment_method.payment_profile_id',
                              'payment_method.payment_method_id']))

    op.create_table(
        'subscription',
        Column('user_profile_id', UUID,
               ForeignKey('user_profile.user_profile_id'), primary_key=True),
        Column('subscription_plan_id', UUID,
               ForeignKey('subscription_plan.subscription_plan_id'), primary_key=True),
        Column('payment_demand_id', UUID, primary_key=True),
        Column('payment_profile_id', UUID, nullable=False),
        Column('payment_method_id', UUID, nullable=False),
        Column('status', subscription_status, nullable=False),
        Column('processor_charge_id', String, nullable=False),
        Column('started_at', DateTime, nullable=False, server_default=utcnow),
        Column('current_status_at', DateTime, nullable=False, server_default=utcnow),
        Column('current_status_until', DateTime, server_default=utcnow),
        ForeignKeyConstraint(['subscription_plan_id', 'payment_demand_id'],
                             ['payment_demand.subscription_plan_id',
                              'payment_demand.payment_demand_id']),
        ForeignKeyConstraint(['user_profile_id', 'payment_profile_id'],
                             ['payment_profile.user_profile_id',
                              'payment_profile.payment_profile_id']),
        ForeignKeyConstraint(['user_profile_id', 'payment_profile_id', 'payment_method_id'],
                             ['payment_method.user_profile_id', 'payment_method.payment_profile_id',
                              'payment_method.payment_method_id']))
    op.create_unique_constraint('uq_user_subscription_plan', 'subscription',
                                ['user_profile_id', 'subscription_plan_id'])

    op.create_table(
        'subscription_payment',
        Column('transaction_id', Integer, ForeignKey('payment_transaction.transaction_id'),
               primary_key=True, autoincrement=False),
        Column('user_profile_id', UUID,
               ForeignKey('user_profile.user_profile_id'), nullable=False),
        Column('subscription_plan_id', UUID,
               ForeignKey('subscription_plan.subscription_plan_id'), nullable=False),
        Column('payment_demand_id', UUID, nullable=True),
        ForeignKeyConstraint(['user_profile_id', 'subscription_plan_id', 'payment_demand_id'],
                             ['subscription.user_profile_id',
                              'subscription.subscription_plan_id',
                              'subscription.payment_demand_id']))

    op.execute("""
        CREATE FUNCTION tg_raise_on_ts_update() RETURNS trigger as $tg$
            DECLARE
                colname TEXT;
            BEGIN
                colname := TG_ARGV[0];
                RAISE '[TIMESTAMP_IMMUTABLE] % must not be altered', colname;
            END;
        $tg$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE FUNCTION tg_update_subscription_current_status_at_ts() RETURNS trigger AS $tg$
            BEGIN
                NEW.current_status_at = timezone('UTC', now());
                RETURN NEW;
            END;
        $tg$ LANGUAGE plpgsql;""")
    op.execute("""
        CREATE TRIGGER subscription_status_update
            BEFORE UPDATE OF status ON subscription
            FOR EACH ROW
            WHEN (OLD.status IS DISTINCT FROM NEW.status)
            EXECUTE PROCEDURE tg_update_subscription_current_status_at_ts();""")
    op.execute("""
        CREATE TRIGGER subscription_started_at_update
            BEFORE UPDATE OF started_at ON subscription
            FOR EACH ROW
            WHEN (OLD.started_at IS DISTINCT FROM NEW.started_at)
            EXECUTE PROCEDURE tg_raise_on_ts_update('started_at');""")
    op.execute("""
        CREATE TRIGGER subscription_current_status_at_update
            BEFORE UPDATE OF current_status_at ON subscription
            FOR EACH ROW
            WHEN (OLD.started_at IS DISTINCT FROM NEW.started_at)
            EXECUTE PROCEDURE tg_raise_on_ts_update('current_status_at');""")


def downgrade():
    op.drop_table('subscription_payment')
    op.drop_table('subscription')
    op.drop_table('payment_transaction')
    op.drop_table('payment_method')
    op.drop_table('payment_profile')
    iso_4217_currency.create(op.get_bind())

    subscription_status.drop(op.get_bind())
    payment_method_type.drop(op.get_bind())
    payment_method_status.drop(op.get_bind())

    op.execute("DROP FUNCTION tg_raise_on_ts_update")
    op.execute("DROP FUNCTION tg_update_subscription_current_status_at_ts")
