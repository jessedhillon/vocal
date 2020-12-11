from decimal import Decimal
from typing import Union, Optional
from uuid import UUID

import sqlalchemy.exc
from sqlalchemy import func as f
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import alias, exists, false, join, literal, select, true

from vocal.constants import ISO4217Currency, SubscriptionPlanStatus, PaymentDemandType,\
        PaymentDemandPeriod
from vocal.api.util import operation
from vocal.api.storage.record import Recordset, SubscriptionPlanPaymentDemandRecord
from vocal.api.storage.sql import subscription_plan, payment_demand


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
        values(status=SubscriptionPlanStatus.Active.value,
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
        'period': period.value,
        'amount': amount,
        'demand_type': PaymentDemandType.Periodic.value,
    }
    if iso_currency is not None:
        values['iso_currency'] = ISO4217Currency(iso_currency).value
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
        'demand_type': PaymentDemandType.Immediate.value,
    }
    if iso_currency is not None:
        values['iso_currency'] = ISO4217Currency(iso_currency).value
    elif non_iso_currency is not None:
        values['non_iso_currency'] = non_iso_currency.upper()

    r = await session.execute(payment_demand.insert().
                              values(**values).
                              returning(payment_demand.c.payment_demand_id))
    return r.scalar()


@operation
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
                 (subscription_plan.c.status == SubscriptionPlanStatus.Active.value).desc(),
                 (payment_demand.c.demand_type == PaymentDemandType.Periodic.value).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Daily.value).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Weekly.value).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Monthly.value).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Quarterly.value).desc(),
                 (payment_demand.c.period == PaymentDemandPeriod.Annually.value).desc())
    rs = await session.execute(q)
    return Recordset(SubscriptionPlanPaymentDemandRecord.unmarshal_result(rs))
