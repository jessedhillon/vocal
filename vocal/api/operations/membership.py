import calendar
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union, Optional
from uuid import UUID

import sqlalchemy.exc
from sqlalchemy import func as f
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import alias, exists, false, join, literal, select, true

from vocal.constants import ISO4217Currency, SubscriptionPlanStatus, PaymentDemandType,\
        PaymentDemandPeriod, SubscriptionStatus
from vocal.util import dates
from vocal.api.util import operation
from vocal.api.storage.record import Recordset, SubscriptionPlanPaymentDemandRecord,\
        SubscriptionRecord
from vocal.api.storage.sql import subscription_plan, payment_demand, subscription


PaymentDemandDesc = Union[tuple[PaymentDemandType, PaymentDemandPeriod, Decimal,
                                Optional[ISO4217Currency], Optional[str]],
                          tuple[PaymentDemandType, Decimal, Optional[ISO4217Currency],
                                Optional[str]]]


@operation
async def create_subscription_plan(session: AsyncSession, description: str,
                                   payment_demands: tuple[PaymentDemandDesc],
                                   rank: Optional[int]=None, name: Optional[str]=None
                                   ) -> UUID:
    r = await session.execute(
        subscription_plan.
        insert().
        values(status=SubscriptionPlanStatus.Active,
               rank=rank,
               name=name,
               description=description).
        returning(subscription_plan.c.subscription_plan_id))
    plan_id = r.scalar()

    for (demand_type, *args) in payment_demands:
        if demand_type is PaymentDemandType.Periodic:
            await add_periodic_payment_demand(plan_id, *args).execute(session)
        elif demand_type is PaymentDemandType.Immediate:
            await add_immediate_payment_demand(plan_id, *args).execute(session)
        else:
            ValueError(demand_type)
    return plan_id


@operation
async def add_periodic_payment_demand(session: AsyncSession, subscription_plan_id: UUID,
                                      period: PaymentDemandPeriod, amount: Decimal,
                                      iso_currency: Optional[ISO4217Currency]=None,
                                      non_iso_currency: Optional[str]=None
                                      ) -> UUID:
    if iso_currency is not None and non_iso_currency is not None:
        raise ValueError("only one of iso_currency or non_iso_currency must be specified")

    values = {
        'subscription_plan_id': subscription_plan_id,
        'period': period,
        'amount': amount,
        'demand_type': PaymentDemandType.Periodic,
    }
    if iso_currency is not None:
        values['iso_currency'] = ISO4217Currency(iso_currency)
    elif non_iso_currency is not None:
        values['non_iso_currency'] = non_iso_currency.upper()

    r = await session.execute(payment_demand.
                              insert().
                              values(**values).
                              returning(payment_demand.c.payment_demand_id))
    return r.scalar()


@operation
async def add_immediate_payment_demand(session: AsyncSession, subscription_plan_id: UUID,
                                       amount: Decimal,
                                       iso_currency: Optional[ISO4217Currency]=None,
                                       non_iso_currency: Optional[str]=None
                                       ) -> UUID:
    if iso_currency is not None and non_iso_currency is not None:
        raise ValueError("only one of an ISO currency or non-ISO currency must be specified")

    values = {
        'subscription_plan_id': subscription_plan_id,
        'amount': amount,
        'demand_type': PaymentDemandType.Immediate,
    }
    if iso_currency is not None:
        values['iso_currency'] = ISO4217Currency(iso_currency)
    elif non_iso_currency is not None:
        values['non_iso_currency'] = non_iso_currency.upper()

    r = await session.execute(payment_demand.insert().
                              values(**values).
                              returning(payment_demand.c.payment_demand_id))
    return r.scalar()


@operation(record_cls=SubscriptionPlanPaymentDemandRecord)
async def get_subscription_plans(session: AsyncSession) -> Recordset:
    q = select(subscription_plan.c.subscription_plan_id,
               subscription_plan.c.status,
               subscription_plan.c.rank,
               subscription_plan.c.name,
               subscription_plan.c.description,
               payment_demand.c.payment_demand_id,
               payment_demand.c.demand_type,
               payment_demand.c.period,
               payment_demand.c.amount,
               payment_demand.c.iso_currency,
               payment_demand.c.non_iso_currency).\
        select_from(subscription_plan).\
        join(payment_demand).\
        order_by(subscription_plan.c.subscription_plan_id,
                 (subscription_plan.c.status == SubscriptionPlanStatus.Active).desc(),
                 (payment_demand.c.demand_type == PaymentDemandType.Periodic).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Daily).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Weekly).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Monthly).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Quarterly).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Annually).desc())
    return await session.execute(q)


@operation(SubscriptionPlanPaymentDemandRecord, single_result=True)
async def get_subscription_plan(session: AsyncSession, subscription_plan_id: UUID=None,
                                payment_demand_id: UUID=None
                                ) -> Result:
    if not any([subscription_plan_id , payment_demand_id]):
        raise ValueError("one of subscription_plan_id, payment_demand_id are required")

    q = select(subscription_plan.c.subscription_plan_id,
               subscription_plan.c.status,
               subscription_plan.c.rank,
               subscription_plan.c.name,
               subscription_plan.c.description,
               payment_demand.c.payment_demand_id,
               payment_demand.c.demand_type,
               payment_demand.c.period,
               payment_demand.c.amount,
               payment_demand.c.iso_currency,
               payment_demand.c.non_iso_currency).\
        select_from(subscription_plan).\
        join(payment_demand).\
        order_by(subscription_plan.c.subscription_plan_id,
                 (subscription_plan.c.status == SubscriptionPlanStatus.Active).desc(),
                 (payment_demand.c.demand_type == PaymentDemandType.Periodic).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Daily).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Weekly).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Monthly).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Quarterly).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Annually).desc())

    if subscription_plan_id is not None:
        q = q.where(subscription_plan.c.subscription_plan_id == subscription_plan_id)
    if payment_demand_id is not None:
        q = q.where(payment_demand.c.payment_demand_id == payment_demand_id)

    return await session.execute(q)


@operation(SubscriptionRecord, single_result=True)
async def create_subscription(session: AsyncSession, user_profile_id: UUID,
                              subscription_plan_id: UUID, payment_demand_id: UUID,
                              payment_profile_id: UUID, payment_method_id: UUID,
                              processor_charge_id: str
                              ) -> Result:
    plans = await get_subscription_plan(
                      subscription_plan_id=subscription_plan_id,
                      payment_demand_id=payment_demand_id).\
                  execute(session)

    today = datetime.today()
    pd = plans[0]
    if pd.period is PaymentDemandPeriod.Daily:
        good_until = today + timedelta(days=1)
    elif pd.period is PaymentDemandPeriod.Weekly:
        good_until = today + timedelta(days=7)
    elif pd.period is PaymentDemandPeriod.Monthly:
        good_until = dates.add_months(today, 1)
    elif pd.period is PaymentDemandPeriod.Quarterly:
        good_until = dates.add_months(today, 3)
    elif pd.period is PaymentDemandPeriod.Annually:
        good_until = dates.add_months(today, 12)

    return await session.execute(
        subscription.\
        insert().\
        values(user_profile_id=user_profile_id,
               subscription_plan_id=subscription_plan_id,
               payment_demand_id=payment_demand_id,
               payment_profile_id=payment_profile_id,
               payment_method_id=payment_method_id,
               status=SubscriptionStatus.Current,
               processor_charge_id=processor_charge_id,
               current_status_until=good_until).\
        returning(subscription.c.user_profile_id,
                  subscription.c.subscription_plan_id,
                  subscription.c.payment_demand_id,
                  subscription.c.payment_profile_id,
                  subscription.c.payment_method_id,
                  subscription.c.processor_charge_id,
                  subscription.c.status,
                  subscription.c.started_at,
                  subscription.c.current_status_until))


@operation(SubscriptionRecord)
async def get_subscriptions(session: AsyncSession, user_profile_id: UUID,
                           subscription_plan_id: Optional[UUID]=None,
                           payment_demand_id: Optional[UUID]=None,
                           ) -> Result:
    q = select(subscription.c.user_profile_id,
               subscription.c.subscription_plan_id,
               subscription.c.payment_demand_id,
               subscription.c.payment_profile_id,
               subscription.c.payment_method_id,
               subscription.c.processor_charge_id,
               subscription.c.status,
               subscription.c.started_at,
               subscription.c.current_status_until).\
        select_from(subscription).\
        where(subscription.c.user_profile_id == user_profile_id)
    if subscription_plan_id is not None:
        q = q.where(subscription.c.subscription_plan_id == subscription_plan_id)
    if payment_demand_id is not None:
        q = q.where(subscription.c.payment_demand_id == payment_demand_id)

    return await session.execute(q)
