from collections.abc import Sequence
from typing import Any, Optional

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.engine.result import Result
from sqlalchemy.engine.row import Row

from vocal.constants import ContactMethodType, ISO4217Currency, SubscriptionPlanStatus,\
        PaymentDemandType, PaymentDemandPeriod, PaymentMethodStatus, PaymentMethodType, UserRole


class Recordset(Sequence):
    def __init__(self, records: list['BaseRecord']):
        self._records = records

    def __len__(self):
        return self._records.__len__()

    def __getitem__(self, index):
        return self._records.__getitem__(index)

    def group_by(self, field_name: str) -> dict[Any, list['BaseRecord']]:
        r = {}
        for rec in self._records:
            v = getattr(rec, field_name)
            r.setdefault(v, []).append(rec)
        return r

class BaseRecord(object):
    @classmethod
    def unmarshal_result(cls, rs: Result) -> Recordset:
        return Recordset([cls.unmarshal_row(row) for row in rs.all()])

    @classmethod
    def unmarshal_row(cls, row: Row) -> 'BaseRecord':
        raise NotImplementedError()


@dataclass(frozen=True)
class UserProfileRecord(BaseRecord):
    user_profile_id: UUID
    display_name: str
    created_at: datetime
    name: str
    role: UserRole
    email_contact_method_id: Optional[UUID]
    email_contact_method_verified: Optional[bool]
    email_address: Optional[str]
    phone_number_contact_method_id: Optional[UUID]
    phone_number_contact_method_verified: Optional[bool]
    phone_number: Optional[str]

    @classmethod
    def unmarshal_row(cls: 'UserProfileRecord', row: Row) -> 'UserProfileRecord':
        return UserProfileRecord(user_profile_id=UUID(row[0]),
                                 display_name=row[1],
                                 created_at=row[2],
                                 name=row[3],
                                 role=UserRole(row[4]),
                                 email_contact_method_id=UUID(row[5]) if row[5] else None,
                                 email_contact_method_verified=row[6],
                                 email_address=row[7],
                                 phone_number_contact_method_id=UUID(row[8]) if row[8] else None,
                                 phone_number_contact_method_verified=row[9],
                                 phone_number=row[10])

@dataclass(frozen=True)
class PaymentProfileRecord(BaseRecord):
    user_profile_id: UUID
    payment_profile_id: UUID
    processor_id: str
    processor_customer_profile_id: str

    @classmethod
    def unmarshal_row(cls, row: Row) -> 'PaymentProfileRecord':
        return cls(user_profile_id=UUID(row[0]),
                   payment_profile_id=UUID(row[1]),
                   processor_id=row[2],
                   processor_customer_profile_id=row[3])


@dataclass(frozen=True)
class PaymentMethodRecord(BaseRecord):
    user_profile_id: UUID
    payment_profile_id: UUID
    processor_id: str
    processor_customer_profile_id: str
    payment_method_id: UUID
    processor_payment_method_id: UUID
    payment_method_type: PaymentMethodType
    payment_method_family: str
    display_name: str
    safe_account_number_fragment: str
    status: PaymentMethodStatus
    expires_after: datetime

    @classmethod
    def unmarshal_row(cls, row: Row) -> 'PaymentMethodRecord':
        return cls(user_profile_id=UUID(row[0]),
                   payment_profile_id=UUID(row[1]),
                   processor_id=row[2],
                   processor_customer_profile_id=row[3],
                   payment_method_id=UUID(row[4]),
                   processor_payment_method_id=row[5],
                   payment_method_type=PaymentMethodType(row[6]),
                   payment_method_family=row[7],
                   display_name=row[8],
                   safe_account_number_fragment=row[9],
                   status=PaymentMethodStatus(row[10]),
                   expires_after=row[11])


@dataclass(frozen=True)
class ContactMethodRecord(BaseRecord):
    user_profile_id: UUID
    contact_method_id: UUID
    contact_method_type: ContactMethodType.Email
    verified: bool


@dataclass(frozen=True)
class EmailContactMethodRecord(ContactMethodRecord):
    email_address: str

    @classmethod
    def unmarshal_row(cls: 'EmailContactMethodRecord', row: Row) -> 'EmailContactMethodRecord':
        if row[3] is not ContactMethodType.Email.value:
            raise ValueError(f"wrong contact_method_type for email: {row[3]}")
        return EmailContactMethodRecord(user_profile_id=UUID(row[0]),
                                        contact_method_id=UUID(row[1]),
                                        contact_method_type=ContactMethodType.Email,
                                        verified=row[2],
                                        email_address=row[4])


@dataclass(frozen=True)
class PhoneContactMethodRecord(ContactMethodRecord):
    phone_number: str

    @classmethod
    def unmarshal_row(cls: 'PhoneContactMethodRecord', row: Row) -> 'PhoneContactMethodRecord':
        if row[3] is not ContactMethodType.Phone.value:
            raise ValueError(f"wrong contact_method_type for phone number: {row[3]}")
        return PhoneContactMethodRecord(user_profile_id=UUID(row[0]),
                                        contact_method_id=UUID(row[1]),
                                        contact_method_type=ContactMethodType.Phone,
                                        verified=row[2],
                                        phone_number=row[4])


@dataclass(frozen=True)
class SubscriptionPlanPaymentDemandRecord(BaseRecord):
    subscription_plan_id: UUID
    status: SubscriptionPlanStatus
    rank: Optional[int]
    name: Optional[str]
    description: str
    payment_demand_id: UUID
    demand_type: PaymentDemandType
    period: Optional[PaymentDemandPeriod]
    amount: Decimal
    iso_currency: Optional[ISO4217Currency]
    non_iso_currency: Optional[str]

    @classmethod
    def unmarshal_row(cls: 'SubscriptionPlanPaymentDemandRecord',
                      row: Row,
                      ) -> 'SubscriptionPlanPaymentDemandRecord':
        return SubscriptionPlanPaymentDemandRecord(
            subscription_plan_id=UUID(row[0]),
            status=SubscriptionPlanStatus(row[1]),
            rank=row[2],
            name=row[3],
            description=row[4],
            payment_demand_id=UUID(row[5]),
            demand_type=PaymentDemandType(row[6]),
            period=PaymentDemandPeriod(row[7]) if row[7] else None,
            amount=row[8],
            iso_currency=ISO4217Currency(row[9]) if row[9] else None,
            non_iso_currency=row[10])
