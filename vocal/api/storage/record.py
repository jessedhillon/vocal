from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


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
