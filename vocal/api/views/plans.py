from aiohttp.web import HTTPAccepted, HTTPBadRequest, HTTPUnauthorized, Response, json_response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.constants import PaymentDemandType
from vocal.api.models.membership import SubscriptionPlan
from vocal.api.models.requests import CreateSubscriptionPlanRequest
from vocal.api.security import Capabilities as caps
from vocal.util.web import with_context, with_session, json_response


@json_response
@util.message
@with_session(new=True)
@with_context
async def get_subscription_plans(request, session, ctx):
    async with op.session(ctx) as ss:
        plans = await op.membership.\
            get_subscription_plans().\
            execute(ss)

    return SubscriptionPlan.unmarshal_recordset(plans)


@json_response
@util.message
@with_session(new=True)
@with_context
@security.requires(caps.PlanCreate)
async def create_subscription_plan(request, session, ctx):
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
