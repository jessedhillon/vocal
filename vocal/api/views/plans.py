from aiohttp.web import HTTPAccepted, HTTPBadRequest, HTTPUnauthorized, Response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.config import AppConfig
from vocal.api.constants import PaymentDemandType
from vocal.api.models.membership import SubscriptionPlan
from vocal.api.models.requests import CreateSubscriptionPlanRequest
from vocal.api.security import AuthnSession, Capability


async def get_subscription_plans(request, ctx: AppConfig, session: AuthnSession):
    async with op.session(ctx) as ss:
        plans = await op.membership.\
            get_subscription_plans().\
            returning(SubscriptionPlan).\
            execute(ss)

    return plans


@security.requires(Capability.PlanCreate)
async def create_subscription_plan(request, ctx: AppConfig, session: AuthnSession):
    plan = CreateSubscriptionPlanRequest.unmarshal_request(await request.json())
    async with op.session(ctx) as ss:
        pds = []
        for pd in plan.payment_demands:
            if pd.demand_type is PaymentDemandType.Periodic:
                pds.append((pd.demand_type, pd.period, pd.amount,
                            pd.iso_currency, pd.non_iso_currency))
            elif pd.demand_type is PaymentDemandType.Immediate:
                pds.append((pd.demand_type, pd.amount, pd.iso_currency, pd.non_iso_currency))
            else:
                raise ValueError(pd.demand_type)
        plan_id = await op.membership.\
            create_subscription_plan(rank=plan.rank, name=plan.name,
                                     description=plan.description,
                                     payment_demands=pds).\
            execute(ss)
    return plan_id
