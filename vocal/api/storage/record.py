from collections.abc import Sequence
from typing import Any, Callable, Optional, List, Union

import itertools
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import sqlalchemy.exc
from sqlalchemy.engine.result import Result
from sqlalchemy.engine.row import Row

from vocal.constants import ContactMethodType, ISO4217Currency, SubscriptionPlanStatus,\
        PaymentDemandType, PaymentDemandPeriod, PaymentMethodStatus, PaymentMethodType, UserRole,\
        SubscriptionStatus


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

    def find(self, keyf: Callable[['BaseRecord'], bool]=None, **kwargs):
        if keyf is not None:
            for rec in self._records:
                if keyf(rec):
                    return rec
            return None

        elif kwargs:
            for rec in self._records:
                match = False
                for key, val in kwargs.items():
                    match = (getattr(rec, key) == val)
                if match:
                    return rec

        raise RuntimeError("find() must be called with key function or kwargs")

    def find_all(self, keyf: Callable[['BaseRecord'], bool]=None, **kwargs):
        results = []
        if keyf is not None:
            for rec in self._records:
                if keyf(rec):
                    results.append(rec)
            return results

        elif kwargs:
            for rec in self._records:
                match = False
                for key, val in kwargs.items():
                    match = (getattr(rec, key) == val)
                if match:
                    results.append(rec)
            return results

        raise RuntimeError("find() must be called with key function or kwargs")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._records}>"


class BaseRecord(object):
    @classmethod
    def group_logical(cls, rs: Result) -> List[Row]:
        return rs.all()

    @classmethod
    def unmarshal_single_result(cls, rs: Result) -> Union['BaseRecord', Recordset]:
        lg = cls.group_logical(rs)
        if len(lg) == 0:
            raise sqlalchemy.exc.NoResultFound()
        return cls.unmarshal_row(lg[0])

    @classmethod
    def unmarshal_result(cls, rs: Result, single=False) -> Union['BaseRecord', Recordset]:
        if single:
            return cls.unmarshal_single_result(rs)
        else:
            return Recordset([cls.unmarshal_row(row) for row in rs.all()])

    @classmethod
    def unmarshal_row(cls, row: Row) -> 'BaseRecord':
        raise NotImplementedError()

    def marshal_dict(self) -> dict:
        return asdict(self)


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
        return UserProfileRecord(user_profile_id=row[0],
                                 display_name=row[1],
                                 created_at=row[2],
                                 name=row[3],
                                 role=UserRole(row[4]),
                                 email_contact_method_id=row[5],
                                 email_contact_method_verified=row[6],
                                 email_address=row[7],
                                 phone_number_contact_method_id=row[8],
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
        return cls(user_profile_id=row[0],
                   payment_profile_id=row[1],
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
        return cls(user_profile_id=row[0],
                   payment_profile_id=row[1],
                   processor_id=row[2],
                   processor_customer_profile_id=row[3],
                   payment_method_id=row[4],
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

    @classmethod
    def unmarshal_row(cls, row: Row) -> 'ContactMethodRecord':
        cmtype = ContactMethodType(row[3])
        if cmtype is ContactMethodType.Email:
            return EmailContactMethodRecord.unmarshal_row(row)
        elif cmtype is ContactMethodType.Phone:
            return PhoneContactMethodRecord.unmarshal_row(row)
        else:
            raise ValueError(cmtype)


@dataclass(frozen=True)
class EmailContactMethodRecord(ContactMethodRecord):
    email_address: str

    @classmethod
    def unmarshal_row(cls: 'EmailContactMethodRecord', row: Row) -> 'EmailContactMethodRecord':
        if row[3] is not ContactMethodType.Email:
            raise ValueError(f"wrong contact_method_type for email: {row[3]}")
        return EmailContactMethodRecord(user_profile_id=row[0],
                                        contact_method_id=row[1],
                                        contact_method_type=ContactMethodType.Email,
                                        verified=row[2],
                                        email_address=row[4])


@dataclass(frozen=True)
class PhoneContactMethodRecord(ContactMethodRecord):
    phone_number: str

    @classmethod
    def unmarshal_row(cls: 'PhoneContactMethodRecord', row: Row) -> 'PhoneContactMethodRecord':
        if row[3] is not ContactMethodType.Phone:
            raise ValueError(f"wrong contact_method_type for phone number: {row[3]}")
        return PhoneContactMethodRecord(user_profile_id=row[0],
                                        contact_method_id=row[1],
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
    def group_logical(cls, rs: Result):
        rows = rs.all()
        if len(rows) == 0:
            raise sqlalchemy.exc.NoResultFound()

        groups = {}
        for row in rows:
            subscription_plan_id = row[0]
            groups.setdefault(subscription_plan_id, []).append(row)
        return list(groups.values())

    @classmethod
    def unmarshal_single_result(cls, rs: Result) -> Recordset:
        groups = cls.group_logical(rs)
        if len(groups) > 1:
            raise sqlalchemy.exc.MultipleResultsFound()
        return Recordset([cls.unmarshal_row(g) for g in groups[0]])

    @classmethod
    def unmarshal_row(cls: 'SubscriptionPlanPaymentDemandRecord',
                      row: Row,
                      ) -> 'SubscriptionPlanPaymentDemandRecord':
        return SubscriptionPlanPaymentDemandRecord(
            subscription_plan_id=row[0],
            status=SubscriptionPlanStatus(row[1]),
            rank=row[2],
            name=row[3],
            description=row[4],
            payment_demand_id=row[5],
            demand_type=PaymentDemandType(row[6]),
            period=PaymentDemandPeriod(row[7]) if row[7] else None,
            amount=row[8],
            iso_currency=ISO4217Currency(row[9]) if row[9] else None,
            non_iso_currency=row[10])


@dataclass(frozen=True)
class SubscriptionRecord(BaseRecord):
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
    def unmarshal_row(cls, row: Row) -> 'SubscriptionRecord':
        return cls(*row)
