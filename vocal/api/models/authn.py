from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

import vocal.api.util as util
from vocal.api.storage.record import UserProfileRecord, ContactMethodRecord
from vocal.constants import AuthnChallengeType, ContactMethodType

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
    def unmarshal(self, obj: dict) -> 'AuthnChallenge':
        return AuthnChallenge(challenge_id=UUID(obj['challenge_id']),
                              challenge_type=AuthnChallengeType(obj['challenge_type']),
                              hint=str(obj['hint']),
                              secret=str(obj['secret']),
                              attempts=int(obj['attempts']))

    @classmethod
    def create_for_user(cls, profile_rec: UserProfileRecord,
                        challenge_type: AuthnChallengeType
                        ) -> 'AuthnChallenge':
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

    @classmethod
    def create_for_contact_method(cls, cm_rec: ContactMethodRecord,
                                  challenge_type: AuthnChallengeType
                                  ) -> 'AuthnChallenge':
        secret = util.generate_otp()
        if cm_rec.contact_method_type is ContactMethodType.Email:
            hint = util.mask_email(cm_rec.email_address)
            chtype = AuthnChallengeType.Email

        elif cm_rec.contact_method_type is ContactMethodType.Phone:
            hint = util.mask_phone_number(cm_rec.phone_number)
            chtype = AuthnChallengeType.SMS

        return cls(challenge_id=uuid4(), challenge_type=challenge_type, hint=hint, secret=secret)


@dataclass
class AuthnChallengeResponse(ViewModel):
    challenge_id: UUID
    passcode: str



@dataclass
@define_view('session_id', name='public')
class AuthnSession(ViewModel):
    authenticated: bool
    session_id: UUID
    user_profile_id: UUID
    require_challenges: list[AuthnChallengeType]
    pending_challenge: Optional[AuthnChallenge]

    @classmethod
    def unmarshal(self, obj: dict) -> 'AuthnSession':
        return AuthnSession(authenticated=bool(obj['authenticated']),
                            session_id=UUID(obj['session_id']),
                            user_profile_id=UUID(obj['user_profile_id']),
                            require_challenges=[AuthnChallengeType(ct)
                                                for ct in obj.get('require_challenges', [])],
                            pending_challenge=AuthnChallenge.unmarshal(obj['pending_challenge'])
                                              if obj.get('pending_challenge') else None)
