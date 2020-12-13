from decimal import Decimal

import vocal.api.operations as op
from vocal.api.models.membership import PaymentDemandType, PaymentDemandPeriod,\
    SubscriptionPlan

from .. import DatabaseTestCase


class MembershipOperationsTestCase(DatabaseTestCase):
    async def test_create_and_get_plan(self):
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

            plans = await op.membership.get_subscription_plans().execute(ss)
        assert len(plans) == 4

        assert plans[0].demand_type is PaymentDemandType.Periodic
        assert plans[1].demand_type is PaymentDemandType.Periodic
        assert plans[2].demand_type is PaymentDemandType.Periodic
        assert plans[3].demand_type is PaymentDemandType.Immediate

        assert plans[0].period is PaymentDemandPeriod.Monthly
        assert plans[1].period is PaymentDemandPeriod.Quarterly
        assert plans[2].period is PaymentDemandPeriod.Annually
        assert plans[3].period is None

        assert plans[0].amount == Decimal('10.0')
        assert plans[1].amount == Decimal('25.0')
        assert plans[2].amount == Decimal('90.0')
        assert plans[3].amount == Decimal('250.0')

        s = {p.subscription_plan_id for p in plans}
        assert len(s) == 1

    async def test_get_plan(self):
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

            plans = await op.membership.\
                get_subscription_plans().\
                unmarshal_with(SubscriptionPlan).\
                execute(ss)

            p = plans[0]
            assert len(plans) == 1
            assert len(p.payment_demands) == 4
