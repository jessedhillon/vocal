import pytest
from contextlib import asynccontextmanager

import sqlalchemy.ext.asyncio
from sqlalchemy.exc import DBAPIError, IntegrityError

from vocal.api.storage.sql import user_profile, contact_method, phone_contact_method,\
        email_contact_method, payment_demand, subscription_plan, subscription

from . import DatabaseTestCase


class SqlTestCase(DatabaseTestCase):
    @asynccontextmanager
    async def get_session(self):
        async with sqlalchemy.ext.asyncio.AsyncSession(self.engine) as ss:
            async with ss.begin():
                yield ss

    async def setUpAsync(self):
        await super().setUpAsync()

        self.engine = self.appctx.storage.get()
        async with self.get_session() as ss:
            r = await ss.execute(
                user_profile.insert().
                    values(display_name='Jesse', name='Jesse Dhillon', role='superuser').
                    returning(user_profile.c.user_profile_id))
            self.user_profile_id = r.scalar()

            r = await ss.execute(
                contact_method.insert().
                    values(user_profile_id=self.user_profile_id,
                           contact_method_type='phone',
                           verified=True).
                    returning(contact_method.c.contact_method_id))
            self.contact_method_id = r.scalar()

            r = await ss.execute(
                phone_contact_method.insert().
                    values(user_profile_id=self.user_profile_id,
                           contact_method_id=self.contact_method_id,
                           phone_number='+14155551212').
                    returning(phone_contact_method.c.contact_method_id))
            self.phone_contact_method_id = r.scalar()

            r = await ss.execute(
                subscription_plan.insert().
                    values(description="Foo Bar Plan").
                    returning(subscription_plan.c.subscription_plan_id))
            self.subscription_plan_id = r.scalar()

            r = await ss.execute(
                payment_demand.insert().
                    values(subscription_plan_id=self.subscription_plan_id,
                           demand_type='periodic',
                           amount=28.0,
                           iso_currency='USD',
                           period='monthly').
                    returning(payment_demand.c.payment_demand_id))
            self.payment_demand_id = r.scalar()

    async def test_cannot_update_verified_phone(self):
        with pytest.raises(DBAPIError) as exc_info:
            async with self.get_session() as ss:
                q = phone_contact_method.\
                        update().\
                        values(phone_number='+18885551234').\
                        where(phone_contact_method.c.contact_method_id == str(self.contact_method_id))
                r = await ss.execute(q)
        assert '[CONTACT_METHOD_VERIFIED]' in str(exc_info.value)

    async def test_cannot_insert_mismatched_contact_method_type(self):
        """when inserting into email_contact_method, contact_method_id must refer to record whose
           contact_method_type is 'email'"""
        with pytest.raises(DBAPIError) as exc_info:
            async with self.get_session() as ss:
                q = email_contact_method.\
                        insert().\
                        values(user_profile_id=self.user_profile_id,
                               contact_method_id=self.contact_method_id,
                               email_address='jesse@dhillon.com')
                r = await ss.execute(q)
        assert '[INCORRECT_CONTACT_METHOD_TYPE]' in str(exc_info.value)

    async def test_cannot_insert_immediate_payment_demand_with_non_null_period_or_currency(self):
        with pytest.raises(IntegrityError) as exc_info:
            async with self.get_session() as ss:
                q = payment_demand.\
                        insert().\
                        values(subscription_plan_id=self.subscription_plan_id,
                               demand_type='immediate',
                               iso_currency='USD',
                               amount=28.0,
                               period='quarterly')
                await ss.execute(q)

        with pytest.raises(IntegrityError) as exc_info:
            async with self.get_session() as ss:
                q = payment_demand.\
                        insert().\
                        values(subscription_plan_id=self.subscription_plan_id,
                               demand_type='immediate',
                               amount=28.0,
                               period='quarterly')
                await ss.execute(q)

    async def test_cannot_modify_payment_demand_with_subscriptions(self):
        async with self.get_session() as ss:
            q = payment_demand.\
                update().\
                values(amount=32.0).\
                where(payment_demand.c.payment_demand_id == self.payment_demand_id)
            await ss.execute(q)

        with pytest.raises(DBAPIError) as exc_info:
            async with self.get_session() as ss:
                q = subscription.\
                    insert().\
                    values(user_profile_id=self.user_profile_id,
                           subscription_plan_id=self.subscription_plan_id,
                           payment_demand_id=self.payment_demand_id,
                           status='current',
                           processor_subscription_id='foobar')
                await ss.execute(q)

                q = payment_demand.\
                    update().\
                    values(amount=35.0).\
                    where(payment_demand.c.payment_demand_id == self.payment_demand_id)
                await ss.execute(q)
        assert '[PAYMENT_DEMAND_HAS_SUBSCRIBERS]' in str(exc_info.value)
