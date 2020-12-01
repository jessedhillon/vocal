from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from vocal.api.constants import ISO4217Currency, PaymentDemandType, PeriodicPaymentDemandPeriod,\
        SubscriptionPlanStatus
from vocal.api.storage.record import Recordset, SubscriptionPlanPaymentDemandRecord

from .base import ViewModel


@dataclass(frozen=True)
class PaymentDemand(ViewModel):
    payment_demand_id: UUID
    demand_type: PaymentDemandType


@dataclass(frozen=True)
class PeriodicPaymentDemand(PaymentDemand):
    period: PeriodicPaymentDemandPeriod
    iso_currency: Optional[ISO4217Currency]
    non_iso_currency: Optional[str]
    amount: Decimal


@dataclass(frozen=True)
class ImmediatePaymentDemand(PaymentDemand):
    iso_currency: Optional[ISO4217Currency]
    non_iso_currency: Optional[str]
    amount: Decimal


@dataclass(frozen=True)
class SubscriptionPlan(ViewModel):
    subscription_plan_id: UUID
    status: SubscriptionPlanStatus
    rank: Optional[int]
    name: Optional[str]
    description: str
    payment_demands: list[PaymentDemand]

    @classmethod
    def unmarshal_recordset(cls, rs: Recordset[SubscriptionPlanPaymentDemandRecord]
                            ) -> list['SubscriptionPlan']:
        plans = {}
        for plan_id, recs in rs.group_by('subscription_plan_id'):
            for rec in recs:
                plans.setdefault(plan_id, {
                    'subscription_plan_id': plan_id,
                    'status': rec.status,
                    'rank': rec.rank,
                    'name': rec.name,
                    'description': rec.description,
                    'payment_demands': [],
                })
                if rec.demand_type is PaymentDemandType.Periodic:
                    plans[plan_id]['payment_demands'].append(
                        PeriodicPaymentDemand(payment_demand_id=rec.payment_demand_id,
                                              demand_type=PaymentDemandType.Periodic,
                                              period=rec.period,
                                              amount=rec.amount,
                                              iso_currency=rec.iso_currency,
                                              non_iso_currency=rec.non_iso_currency))
                elif rec.demand_type is PaymentDemandType.Immediate:
                    plans[plan_id]['payment_demands'].append(
                        ImmediatePaymentDemand(payment_demand_id=rec.payment_demand_id,
                                               demand_type=PaymentDemandType.Immediate,
                                               amount=rec.amount,
                                               iso_currency=rec.iso_currency,
                                               non_iso_currency=rec.non_iso_currency))
        return [cls(**p) for p in plans.values()]
