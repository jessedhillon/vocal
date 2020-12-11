from decimal import Decimal
from dataclasses import dataclass
from typing import Optional, Union
from uuid import UUID

from vocal.constants import AuthnPrincipalType, PaymentDemandType, ISO4217Currency,\
    PaymentDemandPeriod


@dataclass(frozen=True)
class InitiateAuthnSessionRequest:
    principal_name: str
    principal_type: AuthnPrincipalType

    @classmethod
    def unmarshal_request(cls, body: dict) -> 'AuthnSessionRequest':
        return cls(principal_name=str(body['principalName']),
                   principal_type=AuthnPrincipalType(body['principalType']))


@dataclass(frozen=True)
class AuthnChallengeResponseRequest:
    challenge_id: UUID
    passcode: str

    @classmethod
    def unmarshal_request(cls, body: dict) -> 'AuthnChallengeResponseRequest':
        return cls(challenge_id=UUID(body['challenge_id']),
                   passcode=str(body['passcode']))


@dataclass(frozen=True)
class CreateSubscriptionPlanRequest:
    @dataclass(frozen=True)
    class _create_periodic_payment_demand:
        demand_type: PaymentDemandType
        period: PaymentDemandPeriod
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
                        period=PaymentDemandPeriod(pd['period']),
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
