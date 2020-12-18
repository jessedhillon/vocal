import json
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

import vocal.api.operations as op
from vocal.constants import UserRole, PaymentDemandPeriod, PaymentDemandType, PaymentMethodType
from vocal.api.models.membership import SubscriptionPlan
from vocal.api.models.user_profile import SubscriberUserProfile

from sqlalchemy.exc import IntegrityError

from .. import DatabaseTestCase


class UserProfileOperationsTestCase(DatabaseTestCase):
    async def test_create_and_get_user_profile(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234').execute(session)
            rec = await op.user_profile.get_user_profile(profile_id).execute(session)

            assert rec is not None
            assert rec.user_profile_id == profile_id

            fake_uuid = '75a3cffc-641c-4779-9442-31a2995ddec3'
            rec2 = await op.user_profile.get_user_profile(fake_uuid).execute(session)
            assert rec2 is None

    async def test_create_multiple_and_get_user_profile(self):
        profile_ids = await op.execute(self.appctx, [
            op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234'),
            op.user_profile.create_user_profile(
                'Alice G.',
                'Alice Goodwell',
                'password123!',
                UserRole.Subscriber,
                'alice@example.com'),
        ])
        assert all(profile_ids)
        assert len(profile_ids) == 2

        async with op.session(self.appctx) as session:
            jd = await op.user_profile.get_user_profile(profile_ids[0]).execute(session)
            ag = await op.user_profile.get_user_profile(profile_ids[1]).execute(session)
            assert jd.user_profile_id != ag.user_profile_id
            assert jd.display_name == 'Jesse'
            assert ag.display_name == 'Alice G.'

        async with op.session(self.appctx) as session:
            p1 = await op.user_profile.\
                get_user_profile(email_address='alice@example.com').\
                execute(session)
            p2 = await op.user_profile.\
                get_user_profile(phone_number='+14155551234').\
                execute(session)
            assert p1.user_profile_id == ag.user_profile_id
            assert p2.user_profile_id == jd.user_profile_id

    async def test_cannot_create_duplicate_emails(self):
        email = 'jesse@dhillon.com'
        with pytest.raises(ValueError) as excinfo:
            await op.execute(self.appctx, [
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    UserRole.Subscriber,
                    email,
                    '+14155551234'),
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    UserRole.Subscriber,
                    email),
            ])
        assert str(excinfo.value) == f"user profile with email {email} already exists"

    async def test_cannot_create_duplicate_phone_numbers(self):
        pn = '+14155551234'
        with pytest.raises(ValueError) as excinfo:
            await op.execute(self.appctx, [
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    UserRole.Subscriber,
                    None,
                    pn),
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    UserRole.Subscriber,
                    None,
                    pn),
            ])
        assert str(excinfo.value) == f"user profile with phone number {pn} already exists"

    async def test_create_and_get_payment_profile(self):
        async with op.session(self.appctx) as ss:
            profile_id = await op.user_profile.\
                create_user_profile('Jesse',
                                    'Jesse Dhillon',
                                    '123foobar^#@',
                                    UserRole.Subscriber,
                                    'jesse@dhillon.com',
                                    '+14155551234').\
                execute(ss)
            u = await op.user_profile.get_user_profile(user_profile_id=profile_id).execute(ss)
            pp1_id = await op.user_profile.\
                    add_payment_profile(
                        user_profile_id=profile_id,
                        processor_id='com.example',
                        processor_customer_profile_id='foobar').\
                    execute(ss)
            assert pp1_id is not None

            pp2_id = await op.user_profile.\
                    add_payment_profile(
                        user_profile_id=profile_id,
                        processor_id='com.example2',
                        processor_customer_profile_id='foobar2').\
                    execute(ss)
            assert pp2_id is not None and pp1_id is not pp2_id

            for pp_id, proc_id in ((pp1_id, 'com.example'), (pp2_id, 'com.example2')):
                pp = await op.user_profile.\
                    get_payment_profile(user_profile_id=profile_id, processor_id=proc_id).\
                    execute(ss)
                assert pp.payment_profile_id == pp_id
                assert pp.processor_id == proc_id

    async def test_cannot_create_payment_profile_duplicate_processor(self):
        async with op.session(self.appctx) as ss:
            profile_id = await op.user_profile.\
                create_user_profile('Jesse',
                                    'Jesse Dhillon',
                                    '123foobar^#@',
                                    UserRole.Subscriber,
                                    'jesse@dhillon.com',
                                    '+14155551234').\
                execute(ss)

            await op.user_profile.\
                add_payment_profile(
                    user_profile_id=profile_id,
                    processor_id='com.example',
                    processor_customer_profile_id='foobar').\
                execute(ss)

            with pytest.raises(IntegrityError):
                await op.user_profile.\
                    add_payment_profile(
                        user_profile_id=profile_id,
                        processor_id='com.example',
                        processor_customer_profile_id='foo-bar').\
                    execute(ss)


    async def test_get_subscriber_profiles(self):
        async with op.session(self.appctx) as session:
            plan_id = await op.membership.create_subscription_plan(
                rank=1,
                name="Basic member",
                description="- Ad-free podcast episodes\n"
                            "- Access to episodes one week before non-subscribers\n"
                            "- Monthly members-only episode\n",
                payment_demands=(
                    (PaymentDemandType.Periodic, PaymentDemandPeriod.Quarterly,
                     Decimal('25.0'), 'USD'),
                    (PaymentDemandType.Periodic, PaymentDemandPeriod.Annually,
                     Decimal('90.0'), 'USD'),
                    (PaymentDemandType.Periodic, PaymentDemandPeriod.Monthly,
                     Decimal('10.0'), 'USD'),
                    (PaymentDemandType.Immediate, Decimal('250.0'), 'USD'))).\
                execute(session)

            plans = await op.membership.\
                get_subscription_plans().\
                unmarshal_with(SubscriptionPlan).\
                execute(session)

            profile_ids = await op.execute(self.appctx, [
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    UserRole.Subscriber,
                    'jesse@dhillon.com',
                    '+14155551234'),
                op.user_profile.create_user_profile(
                    'Alice G.',
                    'Alice Goodwell',
                    'password123!',
                    UserRole.Subscriber,
                    'alice@example.com'),
            ])

            for i, profile_id in enumerate(profile_ids):
                pd = plans[0].payment_demands[i%4]
                pp_id = await op.user_profile.\
                    add_payment_profile(
                        user_profile_id=profile_id,
                        processor_id='com.example',
                        processor_customer_profile_id=f'customer_{i}').\
                    execute(session)
                pm_id = await op.user_profile.\
                    add_payment_method(
                        user_profile_id=profile_id,
                        payment_profile_id=pp_id,
                        processor_payment_method_id=f'card_{i}',
                        payment_method_type=PaymentMethodType.CreditCard,
                        payment_method_family='test',
                        display_name='TEST 4242',
                        safe_account_number_fragment='4242',
                        expires_after=datetime.today() + timedelta(days=365)).\
                    execute(session)
                await op.membership.\
                    create_subscription(
                        user_profile_id=profile_id,
                        subscription_plan_id=plan_id,
                        payment_demand_id=pd.payment_demand_id,
                        payment_profile_id=pp_id,
                        payment_method_id=pm_id,
                        processor_charge_id=f'charge_{i}').\
                    execute(session)

            subs = await op.user_profile.\
                    get_subscriber_profiles(subscription_plan_id=plans[0].subscription_plan_id).\
                    unmarshal_with(SubscriberUserProfile).\
                    execute(session)

        assert len(subs) == 2
        assert subs[0].subscription.plan.payment_demands[0].period is\
                PaymentDemandPeriod.Monthly
        assert subs[1].subscription.plan.payment_demands[0].period is\
                PaymentDemandPeriod.Quarterly
