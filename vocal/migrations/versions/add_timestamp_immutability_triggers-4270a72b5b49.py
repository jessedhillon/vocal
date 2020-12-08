"""add timestamp, immutability triggers

Revision ID: 4270a72b5b49
Revises: af4e234a4299
Create Date: 2020-12-07 20:20:31.881512

"""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer, String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID
from sqlalchemy.sql import column


import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = '4270a72b5b49'
down_revision = 'af4e234a4299'
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())
v4_uuid = f.gen_random_uuid()


def upgrade():
    # add trigger to guard payment_demand.amount from modification if
    # subscribers are already present (new payment demand should be createdi
    # instead, if desired)
    op.execute("""
        CREATE FUNCTION tg_update_subscription_plan_payment_demand() RETURNS trigger AS $tg$
            DECLARE
                subscount INTEGER;
            BEGIN
                SELECT COUNT(user_profile_id) INTO subscount
                FROM subscription
                JOIN payment_demand USING (subscription_plan_id, payment_demand_id)
                WHERE subscription_plan_id = NEW.subscription_plan_id AND
                      payment_demand_id = NEW.payment_demand_id;
                IF subscount > 0 THEN
                    RAISE EXCEPTION
                        '[PAYMENT_DEMAND_HAS_SUBSCRIBERS] payment demand (%, %) '
                        'has % subscription(s) and cannot be modified',
                        NEW.subscription_plan_id, NEW.payment_demand_id, subscount;
                END IF;
                RETURN NEW;
            END;
        $tg$ LANGUAGE plpgsql;""")
    op.execute("""
        CREATE TRIGGER payment_demand_count_subscribers_update
            BEFORE UPDATE OF status, amount, iso_currency, non_iso_currency
            ON payment_demand
            FOR EACH ROW
            EXECUTE PROCEDURE tg_update_subscription_plan_payment_demand();""")

    # add triggers to guard user_profile.created_at
    op.execute("""CREATE TRIGGER user_profile_created_at_update
                  BEFORE UPDATE OF created_at ON user_profile FOR EACH ROW
                  WHEN (OLD.created_at IS DISTINCT FROM NEW.created_at)
                  EXECUTE PROCEDURE tg_raise_on_ts_update('created_at');""")

    # add triggers for immutable columns
    op.execute("""
        CREATE FUNCTION tg_raise_on_update() RETURNS trigger as $tg$
            DECLARE
                colname regclass;
            BEGIN
                colname := TG_ARGV[0];
                RAISE '[COLUMN_IMMUTABLE] % must not be altered', colname;
            END;
        $tg$ LANGUAGE plpgsql;
    """)
    op.execute("""CREATE TRIGGER payment_demand_type_update
                  BEFORE UPDATE OF demand_type ON payment_demand FOR EACH ROW
                  EXECUTE PROCEDURE tg_raise_on_update('payment_demand.demand_type');""")
    op.execute("""CREATE TRIGGER contact_method_type_update
                  BEFORE UPDATE OF contact_method_type ON contact_method FOR EACH ROW
                  EXECUTE PROCEDURE tg_raise_on_update('contact_method.contact_method_type');""")

    # prevent negative payment demand amounts
    op.create_check_constraint('ck_payment_amount_positive', 'payment_demand',
                               (column('amount') >= 0.00))

    # prevent verified contact methods from changing
    op.execute("""
        CREATE FUNCTION tg_update_verified_contact_method() RETURNS trigger AS $tg$
            DECLARE
                cmverified BOOLEAN;
            BEGIN
                SELECT verified INTO cmverified
                FROM contact_method
                WHERE user_profile_id = NEW.user_profile_id AND
                      contact_method_id = NEW.contact_method_id;
                IF cmverified THEN
                    RAISE EXCEPTION
                        '[CONTACT_METHOD_VERIFIED] contact_method (%, %) '
                        'is marked as verified and cannot be modified',
                        NEW.user_profile_id, NEW.contact_method_id;
                END IF;
                RETURN NEW;
            END;
        $tg$ LANGUAGE plpgsql;""")
    op.execute("""CREATE TRIGGER email_contact_method_update
                  BEFORE UPDATE OF email_address ON email_contact_method FOR EACH ROW
                  EXECUTE PROCEDURE tg_update_verified_contact_method();""")
    op.execute("""CREATE TRIGGER phone_contact_method_update
                  BEFORE UPDATE OF phone_number ON phone_contact_method FOR EACH ROW
                  EXECUTE PROCEDURE tg_update_verified_contact_method();""")

    # ensure verified contact methods match contact_method_type
    op.execute("""
        CREATE FUNCTION tg_check_contact_method_type() RETURNS trigger AS $tg$
            DECLARE
                target_cmtype TEXT;
                cmtype TEXT;
            BEGIN
                target_cmtype := TG_ARGV[0];
                SELECT contact_method_type INTO cmtype
                FROM contact_method
                WHERE user_profile_id = NEW.user_profile_id AND
                      contact_method_id = NEW.contact_method_id;
                IF cmtype != target_cmtype THEN
                    RAISE EXCEPTION
                        '[INCORRECT_CONTACT_METHOD_TYPE] contact_method (%, %) '
                        'has type %, cannot insert into %_contact_method',
                        NEW.user_profile_id, NEW.contact_method_id, cmtype, target_cmtype;
                END IF;
                RETURN NEW;
            END;
        $tg$ LANGUAGE plpgsql;""")
    op.execute("""CREATE TRIGGER email_contact_method_type_check
                  BEFORE INSERT ON email_contact_method FOR EACH ROW
                  EXECUTE PROCEDURE tg_check_contact_method_type('email')""")
    op.execute("""CREATE TRIGGER phone_contact_method_type_check
                  BEFORE INSERT ON phone_contact_method FOR EACH ROW
                  EXECUTE PROCEDURE tg_check_contact_method_type('phone')""")


def downgrade():
    op.execute("DROP TRIGGER user_profile_created_at_update ON user_profile")
    op.execute("DROP TRIGGER email_contact_method_update ON email_contact_method")
    op.execute("DROP TRIGGER phone_contact_method_update ON phone_contact_method")
    op.execute("DROP TRIGGER payment_demand_type_update on payment_demand")
    op.execute("DROP TRIGGER contact_method_type_update on contact_method")
    op.execute("DROP TRIGGER payment_demand_count_subscribers_update on payment_demand")
    op.execute("DROP TRIGGER email_contact_method_type_check ON email_contact_method")
    op.execute("DROP TRIGGER phone_contact_method_type_check ON phone_contact_method")

    op.execute("DROP FUNCTION tg_update_subscription_plan_payment_demand")
    op.execute("DROP FUNCTION tg_update_verified_contact_method")
    op.execute("DROP FUNCTION tg_check_contact_method_type")
    op.execute("DROP FUNCTION tg_raise_on_update")

    op.drop_constraint('ck_payment_amount_positive', 'payment_demand')
