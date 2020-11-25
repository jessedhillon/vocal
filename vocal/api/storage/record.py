from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from vocal.api.models.user_profile import ContactMethodType


@dataclass(frozen=True)
class UserProfileRecord:
    user_profile_id: UUID
    display_name: str
    created_at: datetime
    name: str
    role: str
    email_contact_method_id: str
    email_contact_method_verified: bool
    email_address: str
    phone_number_contact_method_id: str
    phone_number_contact_method_verified: bool
    phone_number: str


@dataclass(frozen=True)
class EmailContactMethodRecord:
    user_profile_id: UUID
    contact_method_id: UUID
    contact_method_type: ContactMethodType
    verified: bool
    email_address: str


@dataclass(frozen=True)
class PhoneContactMethodRecord:
    user_profile_id: UUID
    contact_method_id: UUID
    contact_method_type: ContactMethodType
    verified: bool
    phone_number: str
