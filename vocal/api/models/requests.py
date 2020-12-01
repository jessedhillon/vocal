from decimal import Decimal
from dataclasses import dataclass
from typing import Optional, Union

from vocal.api.constants import PaymentDemandType, ISO4217Currency, PeriodicPaymentDemandPeriod


@dataclass(frozen=True)
class CreateSubscriptionPlanRequest:
    @dataclass(frozen=True)
    class _create_periodic_payment_demand:
        demand_type: PaymentDemandType
        period: PeriodicPaymentDemandPeriod
        amount: Decimal
        iso_currency: Optional[ISO4217Currency]
        non_iso_currency: Optional[str]

    @dataclass(frozen=True)
    class _create_immediate_payment_demand:
        demand_type: PaymentDemandType
        amount: Decimal
        iso_currency: Optional[ISO4217Currency]
        non_iso_currency: Optional[str]

    rank: Optional[int]
    name: Optional[str]
    description: str
    payment_demands: list[Union[_create_periodic_payment_demand, _create_immediate_payment_demand]]

    @classmethod
    def unmarshal_request(cls, body: dict) -> 'CreateSubscriptionPlanRequest':
        pds = []
        for pd in body['payment_demands']:
            pdtype = PaymentDemandType(pd['demand_type'])
            if pdtype is PaymentDemandType.Periodic:
                pds.append(
                    cls._create_periodic_payment_demand(
                        demand_type=pdtype,
                        period=PeriodicPaymentDemandPeriod(pd['period']),
                        amount=Decimal(pd['amount']),
                        iso_currency=ISO4217Currency(pd['iso_currency'])\
                                     if pd.get('iso_currency') else None,
                        non_iso_currency=pd['non_iso_currency']\
                                         if pd.get('non_iso_currency') else None))
            elif pdtype is PaymentDemandType.Immediate:
                pds.append(
                    cls._create_immediate_payment_demand(
                        demand_type=pdtype,
                        amount=Decimal(pd['amount']),
                        iso_currency=ISO4217Currency(pd['iso_currency'])\
                                     if pd.get('iso_currency') else None,
                        non_iso_currency=pd['non_iso_currency']\
                                         if pd.get('non_iso_currency') else None))
            else:
                raise ValueError(pdtype)

        return CreateSubscriptionPlanRequest(rank=body.get('rank'),
                                             name=body.get('name'),
                                             description=body['description'],
                                             payment_demands=tuple(pds))
