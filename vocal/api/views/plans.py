from datetime import datetime

from aiohttp.web import HTTPAccepted, HTTPBadRequest, HTTPUnauthorized, Response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.config import AppConfig
from vocal.api.models.user_profile import PaymentProfile
from vocal.api.models.membership import SubscriptionPlan, Subscription
from vocal.api.models.requests import CreateSubscriptionPlanRequest, CreateSubscriptionRequest
from vocal.api.security import AuthnSession, Capability
from vocal.constants import PaymentDemandType


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


@security.requires(Capability.SubscriptionCreate)
async def create_subscription(request, ctx: AppConfig, session: AuthnSession):
    subscription_plan_id = request.match_info['subscription_plan_id']
    subreq = CreateSubscriptionRequest.unmarshal_request(await request.json())

    async with op.session(ctx) as ss:
        # TODO: just use and expand the get_payment_profile method
        profiles = await op.user_profile.\
            get_payment_methods(user_profile_id=session.user_profile_id,
                                payment_method_id=subreq.payment_method_id).\
            unmarshal_with(PaymentProfile).\
            execute(ss)
        pp = profiles[0]
        pm = pp.payment_methods.find(payment_method_id=subreq.payment_method_id)

        plan = await op.membership.\
            get_subscription_plan(subscription_plan_id=subreq.subscription_plan_id).\
            unmarshal_with(SubscriptionPlan).\
            execute(ss)
        pd = plan.payment_demands.find(payment_demand_id=subreq.payment_demand_id)

        payments = ctx.payments.get()
        processor = payments[pp.processor_id]

        if pd.demand_type is PaymentDemandType.Periodic:
            charge_id = await processor.create_recurring_charge(
                vocal_user_profile_id=session.user_profile_id,
                customer_profile_id=pp.processor_customer_profile_id,
                payment_method_id=pm.processor_payment_method_id,
                start_date=datetime.today(),
                period=pd.period,
                amount=pd.amount,
                iso_currency=pd.iso_currency,
                non_iso_currency=pd.non_iso_currency)
            return await op.membership.\
                create_subscription(
                    user_profile_id=session.user_profile_id,
                    subscription_plan_id=plan.subscription_plan_id,
                    payment_demand_id=pd.payment_demand_id,
                    payment_profile_id=pp.payment_profile_id,
                    payment_method_id=pm.payment_method_id,
                    processor_charge_id=charge_id).\
                unmarshal_with(Subscription).\
                execute(ss)
        elif pd.demand_type is PaymentDemandType.Immediate:
            charge_id = await processor.create_immediate_charge(
                vocal_user_profile_id=session.user_profile_id,
                customer_profile_id=pp.processor_customer_profile_id,
                payment_method_id=pm.processor_payment_method_id,
                amount=pd.amount,
                iso_currency=pd.iso_currency,
                non_iso_currency=pd.non_iso_currency)
            return await op.membership.\
                create_subscription(
                    user_profile_id=session.user_profile_id,
                    subscription_plan_id=plan.subscription_plan_id,
                    payment_demand_id=pd.payment_demand_id,
                    payment_profile_id=pp.payment_profile_id,
                    payment_method_id=pm.payment_method_id,
                    processor_charge_id=charge_id).\
                unmarshal_with(Subscription).\
                execute(ss)
        else:
            raise ValueError(pd.demand_type)
