from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from vocal.api.storage.record import UserProfileRecord, PaymentProfileRecord,\
    PaymentMethodRecord, Recordset, SubscriptionPlanPaymentDemandRecord
from vocal.constants import ContactMethodType, PaymentMethodStatus, PaymentMethodType, UserRole,\
    PaymentDemandType, PaymentDemandPeriod, ISO4217Currency, SubscriptionStatus

from .base import ViewModel, define_view, model_collection


@dataclass(frozen=True)
class MailingAddress(ViewModel):
    email_address: str
    phone_number: str
    country_code: str
    administrative_area: str
    locality: str
    dependent_locality: str
    postal_code: str
    sorting_code: str
    address_2: str
    address_1: str
    organization: str


@dataclass(frozen=True)
class ContactMethod(ViewModel):
    contact_method_id: UUID
    method: ContactMethodType
    verified: bool


@dataclass(frozen=True)
class MailingAddressContactMethod(ContactMethod):
    value: MailingAddress


@dataclass(frozen=True)
class PhoneNumberContactMethod(ContactMethod):
    value: str


@dataclass(frozen=True)
class EmailContactMethod(ContactMethod):
    value: str


@define_view('payment_method_id', 'payment_method_type', 'payment_method_family', 'display_name',
             'safe_account_number_fragment', 'status', 'expires_after', name='public')
@dataclass(frozen=True)
class PaymentMethod(ViewModel):
    payment_method_id: UUID
    processor_payment_method_id: str
    payment_method_type: PaymentMethodType
    payment_method_family: str
    display_name: str
    safe_account_number_fragment: str
    status: PaymentMethodStatus
    expires_after: datetime

    @classmethod
    def unmarshal_record(cls, rec: PaymentMethodRecord) -> 'PaymentMethod':
        return cls(payment_method_id=rec.payment_method_id,
                   processor_payment_method_id=rec.processor_payment_method_id,
                   payment_method_type=rec.payment_method_type,
                   payment_method_family=rec.payment_method_family,
                   display_name=rec.display_name,
                   safe_account_number_fragment=rec.safe_account_number_fragment,
                   status=rec.status,
                   expires_after=rec.expires_after)


@define_view('payment_profile_id', 'processor_id', 'payment_methods', name='public')
@dataclass(frozen=True)
class PaymentProfile(ViewModel):
    user_profile_id: UUID
    payment_profile_id: UUID
    processor_id: str
    processor_customer_profile_id: str
    payment_methods: list[PaymentMethod] = field(default_factory=model_collection)

    @classmethod
    def unmarshal_recordset(cls, rs: Recordset[PaymentMethodRecord]
                            ) -> Recordset['PaymentProfile']:
        pps = {}
        for k, profs in rs.group_by('payment_profile_id').items():
            for rec in profs:
                if k in pps:
                    prof = pps[k]
                    prof.payment_methods.append(PaymentMethod.unmarshal_record(rec))
                else:
                    pms = model_collection([PaymentMethod.unmarshal_record(rec)])
                    prof = PaymentProfile(
                        user_profile_id=rec.user_profile_id,
                        payment_profile_id=rec.payment_profile_id,
                        processor_id=rec.processor_id,
                        processor_customer_profile_id=rec.processor_customer_profile_id,
                        payment_methods=pms)
                    pps[k] = prof
        return list(pps.values())


@define_view('user_profile_id', 'public', name='public')
@dataclass(frozen=True)
class UserProfile(ViewModel):
    @dataclass(frozen=True)
    class _public(ViewModel):
        display_name: str
        created_at: datetime

    @dataclass(frozen=True)
    class _private(ViewModel):
        name: str
        email_address: Optional[EmailContactMethod]
        phone_number: Optional[PhoneNumberContactMethod]
        billing_address: Optional[MailingAddressContactMethod]

    @dataclass(frozen=True)
    class _auth(ViewModel):
        password: Optional[str]
        role: UserRole

    user_profile_id: UUID
    auth: _auth
    public: _public
    private: _private

    @classmethod
    def unmarshal_record(cls, rec: UserProfileRecord) -> 'UserProfile':
        email = EmailContactMethod(contact_method_id=rec.email_contact_method_id,
                                   verified=rec.email_contact_method_verified,
                                   method=ContactMethodType.Email,
                                   value=rec.email_address)
        phone = PhoneNumberContactMethod(contact_method_id=rec.phone_number_contact_method_id,
                                         verified=rec.phone_number_contact_method_verified,
                                         method=ContactMethodType.Phone,
                                         value=rec.phone_number)
        return cls(
            user_profile_id=rec.user_profile_id,
            auth=cls._auth(password=None, role=UserRole(rec.role)),
            public=cls._public(display_name=rec.display_name, created_at=rec.created_at),
            private=cls._private(name=rec.name, email_address=email, phone_number=phone,
                                 billing_address=None))


@dataclass(frozen=True)
class PaymentDemand(ViewModel):
    payment_demand_id: UUID
    demand_type: PaymentDemandType
    period: Optional[PaymentDemandPeriod]
    amount: Decimal
    iso_currency: Optional[ISO4217Currency]
    non_iso_currency: Optional[str]

    @classmethod
    def unmarshal_record(cls, rec: SubscriptionPlanPaymentDemandRecord) -> 'PaymentDemand':
        return cls(payment_demand_id=rec.payment_demand_id,
                   demand_type=rec.demand_type,
                   period=rec.period,
                   amount=rec.amount,
                   iso_currency=rec.iso_currency,
                   non_iso_currency=rec.non_iso_currency)


@dataclass(frozen=True)
class SubscriptionPlan(ViewModel):
    subscription_plan_id: UUID
    rank: Optional[int]
    name: Optional[str]
    description: str
    payment_demands: Optional[list[PaymentDemand]]

    @classmethod
    def unmarshal_recordset(cls,
                            rs: Recordset[SubscriptionPlanPaymentDemandRecord]
                            ) -> list['SubscriptionPlan']:
        subplans = {}
        for k, plans in rs.group_by('subscription_plan_id').items():
            for rec in plans:
                if k in subplans:
                    plan = subplans[k]
                    plan.payment_demands.append(PaymentDemand.unmarshal_record(rec))
                else:
                    plan = cls.unmarshal_record(rec)
                    subplans[k] = plan
        return list(subplans.values())

    @classmethod
    def unmarshal_record(cls, rec: SubscriptionPlanPaymentDemandRecord) -> 'SubscriptionPlan':
        pds = model_collection([PaymentDemand.unmarshal_record(rec)])
        return cls(subscription_plan_id=rec.subscription_plan_id,
                   rank=rec.rank,
                   name=rec.subscription_plan_name,
                   description=rec.description,
                   payment_demands=pds)


@define_view('user_profile_id', 'public', 'subscription', name='public')
@dataclass(frozen=True)
class SubscriberUserProfile(UserProfile):
    @dataclass(frozen=True)
    class _subscription:
        plan: SubscriptionPlan
        status: SubscriptionStatus
        started_at: datetime
        current_status_until: Optional[datetime]

    subscription: _subscription

    @classmethod
    def unmarshal_record(cls,
                         rec: 'SubscriberUserProfileRecord'
                         ) -> 'SubscriberUserProfileRecord':
        email = EmailContactMethod(contact_method_id=rec.email_contact_method_id,
                                   verified=rec.email_contact_method_verified,
                                   method=ContactMethodType.Email,
                                   value=rec.email_address)
        phone = PhoneNumberContactMethod(contact_method_id=rec.phone_number_contact_method_id,
                                         verified=rec.phone_number_contact_method_verified,
                                         method=ContactMethodType.Phone,
                                         value=rec.phone_number)
        sub = cls._subscription(plan=SubscriptionPlan.unmarshal_record(rec),
                                status=rec.status,
                                started_at=rec.started_at,
                                current_status_until=rec.current_status_until)
        return cls(user_profile_id=rec.user_profile_id,
                   auth=cls._auth(password=None, role=UserRole(rec.role)),
                   public=cls._public(display_name=rec.display_name, created_at=rec.created_at),
                   private=cls._private(name=rec.name, email_address=email, phone_number=phone,
                                        billing_address=None),
                   subscription=sub)
