from dataclasses import dataclass, field
from uuid import UUID, uuid4

import vocal.api.security as security
import vocal.api.util as util
from vocal.api.constants import AuthnChallengeType

from .base import define_view, ViewModel


@dataclass
@define_view('challenge_id', 'challenge_type', 'hint', name='public')
class AuthnChallenge(ViewModel):
    challenge_id: UUID
    challenge_type: AuthnChallengeType
    hint: str
    secret: str
    attempts: int = field(default=0)

    @classmethod
    def create_challenge_for_user(cls, profile_rec, challenge_type):
        if challenge_type is AuthnChallengeType.Email:
            secret = util.generate_otp()
            hint = util.mask_email(profile_rec.email_address)
            if not profile_rec.email_contact_method_verified:
                raise ValueError(f"email {hint} must be verified first")

        elif challenge_type is AuthnChallengeType.SMS:
            secret = util.generate_otp()
            hint = util.mask_email(profile_rec.phone_number)
            if not profile_rec.phone_contact_method_verified:
                raise ValueError("phone {hint} must be verified first")

        elif challenge_type is AuthnChallengeType.Password:
            secret = None
            hint = None

        return cls(challenge_id=uuid4(), challenge_type=challenge_type, hint=hint, secret=secret)


@dataclass
class AuthnChallengeResponse(ViewModel):
    challenge_id: UUID
    passcode: str


@dataclass
@define_view('session_id', name='public')
class AuthnSession(ViewModel):
    session_id: UUID
    user_profile_id: UUID
    require_challenges: list[AuthnChallengeType]
