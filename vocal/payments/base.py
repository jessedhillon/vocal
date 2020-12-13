from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional, NewType

from vocal.constants import ISO3166Country, ISO4217Currency, PaymentDemandPeriod
from vocal.locale.base import Address

from .models import PaymentCredential, ChargeID, CustomerProfileID, PaymentMethodID,\
    RecurringChargeID


class BasePaymentProcessor(object):
    def supports_currency(self, iso_currency: ISO4217Currency, non_iso_currency: str) -> bool:
        raise NotImplementedError()

    def supports_region(self, cc: ISO3166Country) -> bool:
        raise NotImplementedError()

    async def create_customer_profile(self, vocal_user_profile_id: UUID,
                                      customer_profile_id: CustomerProfileID,
                                      name: str, email: str, phone: Optional[str],
                                      address: Optional[Address]
                                      ) -> CustomerProfileID:
        raise NotImplementedError()

    async def add_customer_payment_method(self, customer_profile_id: CustomerProfileID,
                                          credential: PaymentCredential
                                          ) -> PaymentMethodID:
        raise NotImplementedError()

    async def create_immediate_charge(self, vocal_user_profile_id: UUID,
                                      customer_profile_id: CustomerProfileID,
                                      payment_method_id: PaymentMethodID,
                                      start_date: datetime,
                                      amount: Decimal,
                                      iso_currency: Optional[ISO4217Currency]=None,
                                      non_iso_currency: Optional[str]=None
                                      ) -> ChargeID:
        raise NotImplementedError()

    async def create_recurring_charge(self, vocal_user_profile_id: UUID,
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
        raise NotImplementedError()
