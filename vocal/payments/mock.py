from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID, uuid4

from hashids import Hashids

from vocal.locale.en_us import USAddress
from vocal.config import AppConfig
from vocal.constants import ISO3166Country, ISO4217Currency, PaymentDemandPeriod,\
    PaymentMethodType

from .models import PaymentCredential
from .base import BasePaymentProcessor, ChargeID, CustomerProfileID, PaymentMethodID,\
    RecurringChargeID


@dataclass(frozen=True)
class MockPaymentProcessorConfig:
    client_id: str
    secret: str


class MockPaymentProcessor(BasePaymentProcessor):
    processor_id = 'com.example'

    def __init__(self, client_id, secret):
        self.config = MockPaymentProcessorConfig(client_id=client_id, secret=secret)
        self._customers = {}
        self._charges = []

    def _hash(self, n: int) -> str:
        h = Hashids(self.processor_id)
        return h.encode(n)

    def supports_currency(self, iso_currency: Optional[ISO4217Currency]=None,
                          non_iso_currency: Optional[str]=None
                          ) -> bool:
        return iso_currency in {ISO4217Currency.USD}

    def supports_region(config: MockPaymentProcessorConfig, cc: ISO3166Country) -> bool:
        return cc in {ISO3166Country.US}

    async def create_customer_profile(self, vocal_user_profile_id: UUID,
                                      name: str, email: str, phone: Optional[str],
                                      address: Optional[USAddress]=None
                                      ) -> CustomerProfileID:
        profile_id = self._hash(uuid4().int)
        self._customers[profile_id] = {
            'id': profile_id,
            'meta': {
                'description': str(vocal_user_profile_id),
            },
            'name': name,
            'email_address': email,
            'phone_number': phone,
            'address': address,
            'payment_methods': {},
        }
        return profile_id

    async def add_customer_payment_method(self, customer_profile_id: CustomerProfileID,
                                          credential: PaymentCredential
                                          ) -> PaymentMethodID:
        assert customer_profile_id in self._customers
        assert credential.method_type is PaymentMethodType.CreditCard
        payment_method_id = self._hash(uuid4().int)
        self._customers[customer_profile_id]['payment_methods'][payment_method_id] = {
            'id': payment_method_id,
            'card_number': credential.card_number,
            'cvv': credential.cvv,
            'exp': [credential.exp_month, credential.exp_year]
        }
        return payment_method_id

    async def create_recurring_charge(self,
                                      vocal_user_profile_id: UUID,
                                      customer_profile_id: CustomerProfileID,
                                      payment_method_id: PaymentMethodID,
                                      start_date: datetime,
                                      period: PaymentDemandPeriod,
                                      amount: Decimal,
                                      total_periods: Optional[int]=None,
                                      trial_periods: Optional[int]=None,
                                      trial_amount: Optional[Decimal]=None,
                                      iso_currency: Optional[ISO4217Currency]=None,
                                      non_iso_currency: Optional[str]=None
                                      ) -> RecurringChargeID:
        charge_id = self._hash(uuid4().int)
        self._charges.append({
            'timestamp': datetime.utcnow(),
            'customer_profile_id': customer_profile_id,
            'payment_method_id': payment_method_id,
            'start_date': start_date,
            'period': period.value,
            'amount': amount,
            'iso_currency': iso_currency.value,
        })
        # TODO: throw exception to simulate failure
        return charge_id

    async def create_immediate_charge(self,
                                      vocal_user_profile_id: UUID,
                                      customer_profile_id: CustomerProfileID,
                                      payment_method_id: PaymentMethodID,
                                      start_date: datetime,
                                      amount: Decimal,
                                      iso_currency: Optional[ISO4217Currency]=None,
                                      non_iso_currency: Optional[str]=None
                                      ) -> ChargeID:
        charge_id = self._hash(uuid4().int)
        self._charges.append({
            'timestamp': datetime.utcnow(),
            'customer_profile_id': customer_profile_id,
            'payment_method_id': payment_method_id,
            'start_date': start_date.date(),
            'amount': amount,
            'iso_currency': iso_currency.value,
        })
        # TODO: throw exception to simulate failure
        return charge_id


def configure(client_id: str, secret: str) -> MockPaymentProcessor:
    return MockPaymentProcessor(client_id=client_id, secret=secret)
