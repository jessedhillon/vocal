from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from vocal.constants import ISO4217Currency, PaymentDemandType, PaymentDemandPeriod,\
        SubscriptionStatus, SubscriptionPlanStatus
from vocal.api.storage.record import Recordset, SubscriptionPlanPaymentDemandRecord,\
        SubscriptionRecord

from .base import ViewModel, model_collection, define_view


@dataclass(frozen=True)
class PaymentDemand(ViewModel):
    payment_demand_id: UUID
    demand_type: PaymentDemandType


@dataclass(frozen=True)
class PeriodicPaymentDemand(PaymentDemand):
    period: PaymentDemandPeriod
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
    payment_demands: model_collection[PaymentDemand]

    @classmethod
    def unmarshal_recordset(cls, rs: Recordset[SubscriptionPlanPaymentDemandRecord]
                            ) -> model_collection['SubscriptionPlan']:
        plans = {}
        for plan_id, recs in rs.group_by('subscription_plan_id').items():
            plans[plan_id] = cls.unmarshal_record_group(recs)
        return model_collection([v for v in plans.values()])

    @classmethod
    def unmarshal_record_group(cls,
                               recs: list[SubscriptionPlanPaymentDemandRecord]
                               ) -> 'SubscriptionPlan':
        plan = {}
        for rec in recs:
            if not plan:
                plan.update({
                    'subscription_plan_id': rec.subscription_plan_id,
                    'status': rec.status,
                    'rank': rec.rank,
                    'name': rec.name,
                    'description': rec.description,
                    'payment_demands': model_collection([]),
                })
            if rec.demand_type is PaymentDemandType.Periodic:
                plan['payment_demands'].append(
                    PeriodicPaymentDemand(payment_demand_id=rec.payment_demand_id,
                                          demand_type=PaymentDemandType.Periodic,
                                          period=rec.period,
                                          amount=rec.amount,
                                          iso_currency=rec.iso_currency,
                                          non_iso_currency=rec.non_iso_currency))
            elif rec.demand_type is PaymentDemandType.Immediate:
                plan['payment_demands'].append(
                    ImmediatePaymentDemand(payment_demand_id=rec.payment_demand_id,
                                           demand_type=PaymentDemandType.Immediate,
                                           amount=rec.amount,
                                           iso_currency=rec.iso_currency,
                                           non_iso_currency=rec.non_iso_currency))
        return SubscriptionPlan(**plan)


@define_view('subscription_plan_id', 'payment_demand_id', 'payment_method_id',
             'status', 'started_at', 'current_status_until', name='public')
@dataclass(frozen=True)
class Subscription(ViewModel):
    user_profile_id: UUID
    subscription_plan_id: UUID
    payment_demand_id: UUID
    payment_profile_id: UUID
    payment_method_id: UUID
    processor_charge_id: str
    status: SubscriptionStatus
    started_at: datetime
    current_status_until: Optional[datetime]

    @classmethod
    def unmarshal_record(cls, rec: SubscriptionRecord) -> 'Subscription':
        return Subscription(**rec.marshal_dict())
