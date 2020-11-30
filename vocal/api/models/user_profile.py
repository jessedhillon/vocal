from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from vocal.api.constants import ContactMethodType, UserRole
from vocal.api.storage.record import UserProfileRecord

from .base import ViewModel, define_view


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


@define_view('user_profile_id', 'public', name='public')
@dataclass(frozen=True)
class UserProfile(ViewModel):
    user_profile_id: UUID

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

    auth: _auth
    public: _public
    private: _private

    @classmethod
    def unmarshal_record(cls: 'UserProfile', rec: UserProfileRecord) -> 'UserProfile':
        email = EmailContactMethod(contact_method_id=rec.email_contact_method_id,
                                   verified=rec.email_contact_method_verified,
                                   method=ContactMethodType.Email,
                                   value=rec.email_address)
        phone = PhoneNumberContactMethod(contact_method_id=rec.phone_number_contact_method_id,
                                         verified=rec.phone_number_contact_method_verified,
                                         method=ContactMethodType.Phone,
                                         value=rec.phone_number)
        return UserProfile(
            user_profile_id=rec.user_profile_id,
            auth=cls._auth(password=None, role=UserRole(rec.role)),
            public=cls._public(display_name=rec.display_name, created_at=rec.created_at),
            private=cls._private(name=rec.name, email_address=email, phone_number=phone,
                                 billing_address=None))
