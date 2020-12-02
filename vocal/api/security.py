from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Optional
from uuid import UUID

import aiohttp_session
from aiohttp_session import SimpleCookieStorage, Session as BaseSession
from aiohttp_session.redis_storage import RedisStorage
from aiohttp.web_exceptions import HTTPForbidden

from vocal.api.constants import UserRole
from vocal.api.models.user_profile import UserProfile, ContactMethod
from vocal.api.models.authn import AuthnChallenge, AuthnChallengeType


MaxVerificationChallengeAttempts = 3


class Capabilities(Enum):
    Authenticate = 'authn'
    ProfileList = 'profile.list'
    PlanCreate = 'plan.create'


RoleCapabilities = {
    UserRole.Superuser: {Capabilities.Authenticate, Capabilities.ProfileList,
                         Capabilities.PlanCreate},
    UserRole.Manager: {Capabilities.ProfileList},
    UserRole.Creator: {Capabilities.ProfileList},
    UserRole.Subscriber: {Capabilities.ProfileList},
    UserRole.Member: {Capabilities.ProfileList},
}


class AuthnSession(BaseSession):
    def __init__(self, identity, *, data, new, max_age=None):
        if new:
            data = data or {}
            data.update({
                'session': {
                    'authenticated': False,
                    'user_profile_id': None,
                    'required_challenges': [],
                    'pending_challenge': None,
                }
            })
        else:
            session_data = data.get('session', None) if data else None
            if session_data is not None:
                session_data.update({
                    'authenticated': bool(session_data['authenticated']),
                    'user_profile_id': UUID(session_data['user_profile_id'])
                                       if session_data.get('user_profile_id') else None,
                    'required_challenges':\
                        [AuthnChallengeType(ct) for ct in session_data['required_challenges']],
                    'pending_challenge':\
                        AuthnChallenge.unmarshal(session_data['pending_challenge'])
                        if session_data.get('pending_challenge') else None,
                })

        super().__init__(identity, data=data, new=new, max_age=max_age)

    @property
    def authenticated(self) -> bool:
        return self.setdefault('authenticated', False)

    @authenticated.setter
    def authenticated(self, v: bool):
        self._mapping['authenticated'] = v
        self.changed()

    @property
    def user_profile_id(self) -> UUID:
        return self._mapping['user_profile_id']

    @user_profile_id.setter
    def user_profile_id(self, v: UUID):
        self._mapping['user_profile_id'] = v

    @property
    def required_challenges(self) -> list[AuthnChallengeType]:
        return self._mapping['required_challenges']

    def require_challenge(self, v: AuthnChallengeType):
        self._mapping['required_challenges'].append(v)
        self.changed()

    @property
    def pending_challenge(self) -> Optional[AuthnChallenge]:
        return self._mapping['pending_challenge']

    def clear_pending_challenge(self):
        self._mapping['pending_challenge'] = None
        self.changed()

    def next_challenge_for_user(self, u: UserProfile):
        chtype = self.required_challenges.pop(0)
        self._mapping['pending_challenge'] = AuthnChallenge.create_for_user(u, chtype)
        self.changed()

    def next_challenge_for_contact_method(self, cm: ContactMethod):
        chtype = self.required_challenges.pop(0)
        self._mapping['pending_challenge'] = AuthnChallenge.create_for_contact_method(cm, chtype)
        self.changed()


class RedisStorage(RedisStorage):
    async def new_session(self):
        return AuthnSession(None, data=None, new=True, max_age=self.max_age)

    async def load_session(self, request):
        cookie = self.load_cookie(request)
        if cookie is None:
            return AuthnSession(None, data=None, new=True, max_age=self.max_age)
        else:
            with await self._redis as conn:
                key = str(cookie)
                data = await conn.get(self.cookie_name + '_' + key)
                if data is None:
                    return AuthnSession(None, data=None,
                                   new=True, max_age=self.max_age)
                data = data.decode('utf-8')
                try:
                    data = self._decoder(data)
                except ValueError:
                    data = None
                return AuthnSession(key, data=data, new=False, max_age=self.max_age)

class SimpleCookieStorage(SimpleCookieStorage):
    async def new_session(self):
        return AuthnSession(None, data=None, new=True, max_age=self.max_age)

    async def load_session(self, request):
        cookie = self.load_cookie(request)
        if cookie is None:
            return AuthnSession(None, data=None, new=True, max_age=self.max_age)
        else:
            data = self._decoder(cookie)
            return AuthnSession(None, data=data, new=False, max_age=self.max_age)

    async def save_session(self, request, response, session):
        cookie_data = self._encoder(self._get_session_data(session))
        self.save_cookie(response, cookie_data, max_age=session.max_age)


def _as_values(caps):
    return [c.value for c in caps]


def set_role(session, role):
    session['capabilities'] = []
    add_capabilities(session, *RoleCapabilities[role])


def add_capabilities(session, *caps):
    session['capabilities'] = set(session.setdefault('capabilities', [])) | set(caps)
    session.changed()


def remove_capabilities(session, *caps):
    caps = set(_as_values(caps))
    scaps = set(session.setdefault('capabilities', []))
    session['capabilities'] = set(scaps) - set(caps)
    session.changed()


def has_capabilities(session, *caps):
    caps = set(_as_values(caps))
    scaps = set(session.setdefault('capabilities', []))
    return caps <= scaps


def requires(*capabilities):
    def wrapper(handler):
        @wraps(handler)
        async def f(request, *args, **kwargs):
            session = await aiohttp_session.get_session(request)
            if not has_capabilities(session, *capabilities):
                raise HTTPForbidden()
            else:
                return await handler(request, *args, **kwargs)
        return f
    return wrapper
