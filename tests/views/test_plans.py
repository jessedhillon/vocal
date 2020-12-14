import json
from decimal import Decimal

import vocal.api.operations as op
from vocal.api.models.membership import SubscriptionPlan, Subscription
from vocal.api.models.user_profile import PaymentProfile
from vocal.constants import PaymentDemandType, PaymentDemandPeriod, UserRole
from vocal.payments.models import PaymentCredential

from .. import AppTestCase

class PlansViewTestCase(AppTestCase):
    async def test_get_plans(self):
        async with op.session(self.appctx) as ss:
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
                execute(ss)
            assert plan_id is not None

        resp = await self.client.request('GET', '/plans')
        j = await resp.json()
        assert resp.status == 200

        plans = j['data']
        assert len(plans) == 1

        plan = plans[0]
        assert len(plan['payment_demands']) == 4

        pds = plan['payment_demands']
        assert len([pd for pd in pds if pd['demand_type'] == 'immediate']) == 1
        assert len([pd for pd in pds if pd['demand_type'] == 'periodic']) == 3

    async def test_create_plan(self):
        await self.authenticate_as(UserRole.Superuser)
        data = {
            'rank': 1,
            'name': "Basic member",
            'description': "- Ad-free podcast episodes\n"
                           "- Access to episodes one week before non-subscribers\n"
                           "- Monthly members-only episode\n",
            'payment_demands': [{
                'demand_type': 'periodic',
                'period': 'quarterly',
                'amount': '25.0',
                'iso_currency': 'USD',
            }, {
                'demand_type': 'periodic',
                'period': 'annually',
                'amount': '90.0',
                'iso_currency': 'USD',
            }, {
                'demand_type': 'periodic',
                'period': 'monthly',
                'amount': '10.0',
                'iso_currency': 'USD',
            }, {
                'demand_type': 'immediate',
                'amount': '10.0',
                'iso_currency': 'USD',
            }]
        }
        resp = await self.client.request('POST', '/plans', json=data)
        assert resp.status == 200

        resp = await self.client.request('GET', '/plans')
        j = await resp.json()
        assert resp.status == 200

        plans = j['data']
        assert len(plans) == 1

        plan = plans[0]
        assert len(plan['payment_demands']) == 4

        pds = plan['payment_demands']
        assert len([pd for pd in pds if pd['demand_type'] == 'immediate']) == 1
        assert len([pd for pd in pds if pd['demand_type'] == 'periodic']) == 3

    async def test_create_subscription(self):
        profile_id = await self.authenticate_as(UserRole.Superuser)

        async with op.session(self.appctx) as ss:
            u = await op.user_profile.\
                get_user_profile(user_profile_id=profile_id).\
                execute(ss)
            payments = self.appctx.payments.get()
            mock = payments['com.example']
            mp_cust_id = await mock.create_customer_profile(u.user_profile_id, u.name,
                                                            u.email_address, u.phone_number)
            cc = PaymentCredential.unmarshal_request({
                'methodType': 'credit_card',
                'cardNumber': '4242424242424242',
                'expMonth': 12,
                'expYear': 2023,
                'cvv': '444',
            })
            mp_pm_id = await mock.add_customer_payment_method(mp_cust_id, cc)
            pp_id = await op.user_profile.add_payment_profile(
                    user_profile_id=profile_id,
                    processor_id='com.example',
                    processor_customer_profile_id=mp_cust_id).\
                execute(ss)
            pm_id = await op.user_profile.add_payment_method(
                    user_profile_id=profile_id,
                    payment_profile_id=pp_id,
                    processor_payment_method_id=mp_pm_id,
                    payment_method_type=cc.method_type,
                    payment_method_family=cc.method_family,
                    display_name=cc.display_name,
                    safe_account_number_fragment=cc.safe_account_number_fragment,
                    expires_after=cc.expire_after_date).\
                execute(ss)
            profiles = await op.user_profile.get_payment_methods(
                    user_profile_id=profile_id,
                    payment_profile_id=pp_id).\
                unmarshal_with(PaymentProfile).\
                execute(ss)
            plan_id = await op.membership.\
                create_subscription_plan(
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
                execute(ss)
            plans = await op.membership.\
                get_subscription_plans().\
                unmarshal_with(SubscriptionPlan).\
                execute(ss)

        pd = plans[0].payment_demands.find(period=PaymentDemandPeriod.Monthly)
        pm = profiles[0].payment_methods.find(payment_method_id=pm_id)
        body = {
            'paymentMethodId': str(pm.payment_method_id),
            'subscriptionPlanId': str(plans[0].subscription_plan_id),
            'paymentDemandId': str(pd.payment_demand_id),
        }
        resp = await self.client.request('POST', f'/plans/{plan_id}/subscribe', json=body)

        payments = self.appctx.payments.get()
        mock = payments['com.example']

        charge = mock._charges[0]
        async with op.session(self.appctx) as ss:
            subs = await op.membership.\
                get_subscriptions(
                    user_profile_id=profile_id,
                    subscription_plan_id=plans[0].subscription_plan_id).\
                unmarshal_with(Subscription).\
                execute(ss)
            assert len(subs) == 1
        assert charge['amount'] == pd.amount
        assert charge['iso_currency'] == pd.iso_currency.value
        assert charge['period'] == pd.period.value
