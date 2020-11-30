import json
from decimal import Decimal

import vocal.api.operations as op
from vocal.api.constants import PaymentDemandType, PeriodicPaymentDemandPeriod
from vocal.api.models.membership import SubscriptionPlan

from .. import DatabaseTestCase

class PlansViewTestCase(DatabaseTestCase):
    async def test_get_plans(self):
        async with op.session(self.appctx) as ss:
            plan_id = await op.membership.create_subscription_plan(
                rank=1,
                name="Basic member",
                description="- Ad-free podcast episodes\n"
                            "- Access to episodes one week before non-subscribers\n"
                            "- Monthly members-only episode\n",
                payment_demands=(
                    (PaymentDemandType.Periodic, PeriodicPaymentDemandPeriod.Quarterly,
                     Decimal('25.0'), 'USD'),
                    (PaymentDemandType.Periodic, PeriodicPaymentDemandPeriod.Annually,
                     Decimal('90.0'), 'USD'),
                    (PaymentDemandType.Periodic, PeriodicPaymentDemandPeriod.Monthly,
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