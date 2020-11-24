from dataclasses import dataclass, field
from enum import Enum
from typing import List
from uuid import UUID

from .base import define_view, ViewModel


class AuthnChallengeType(Enum):
    Password = 'password'
    Email = 'email'
    SMS = 'sms'
    OTP = 'otp'


@dataclass
@define_view('challenge_id', 'challenge_type', 'hint', name='public')
class AuthnChallenge(ViewModel):
    challenge_id: str
    challenge_type: AuthnChallengeType
    hint: str
    secret: str

@dataclass
@define_view('session_id', name='public')
class AuthnSession(ViewModel):
    session_id: UUID
    user_profile_id: UUID
    require_challenges: List[AuthnChallengeType]
    active_challenge_id: UUID
