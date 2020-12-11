from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Optional
from uuid import UUID

import aiohttp_session
from aiohttp_session import SimpleCookieStorage, Session as BaseSession
from aiohttp_session.redis_storage import RedisStorage
from aiohttp.web_exceptions import HTTPForbidden

from vocal.api.models.user_profile import UserProfile, ContactMethod
from vocal.api.models.authn import AuthnChallenge, AuthnChallengeType
from vocal.constants import UserRole


MaxVerificationChallengeAttempts = 3


class Capability(Enum):
    Authenticate = 'authn'
    ProfileList = 'profile.list'
    PlanCreate = 'plan.create'


RoleCapability = {
    UserRole.Superuser: {Capability.Authenticate, Capability.ProfileList, Capability.PlanCreate},
    UserRole.Manager: {Capability.ProfileList},
    UserRole.Creator: {Capability.ProfileList},
    UserRole.Subscriber: {Capability.ProfileList},
    UserRole.Member: {Capability.ProfileList},
}


class AuthnSession(BaseSession):
    def __init__(self, identity, *, data, new, max_age=None):
        if new:
            data = data or {}
            data.update({
                'session': {
                    'authenticated': False,
                    'capabilities': [],
                    'pending_challenge': None,
                    'required_challenges': [],
                    'user_profile_id': None,
                }
            })
        else:
            session_data = data.get('session', None) if data else None
            if session_data is not None:
                session_data.update({
                    'authenticated': bool(session_data['authenticated']),
                    'capabilities': [Capability(cap) for cap in session_data['capabilities']],
                    'pending_challenge':\
                        AuthnChallenge.unmarshal(session_data['pending_challenge'])
                        if session_data.get('pending_challenge') else None,
                    'required_challenges':\
                        [AuthnChallengeType(ct) for ct in session_data['required_challenges']],
                    'user_profile_id': UUID(session_data['user_profile_id'])
                                       if session_data.get('user_profile_id') else None,
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
    def capabilities(self) -> list[Capability]:
        return self._mapping['capabilities']

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

    def set_role(self, role: UserRole):
        self._mapping['capabilities'] = []
        self.add_capabilities(*RoleCapability[role])

    def add_capabilities(self, *caps):
        self._mapping['capabilities'] = set(self._mapping['capabilities']) | set(caps)
        self.changed()

    def remove_capabilities(self, *caps):
        self._mapping['capabilities'] = set(self._mapping['capabilities']) - set(caps)
        self.changed()

    def has_capabilities(self, *caps):
        return set(caps) <= set(self._mapping['capabilities'])


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


def requires(*capabilities):
    def wrapper(handler):
        @wraps(handler)
        async def f(request, __requires_session: AuthnSession, *args, **kwargs):
            if not __requires_session.has_capabilities(*capabilities):
                raise HTTPForbidden()
            else:
                return await handler(request, *args, **kwargs)
        f.__annotations__['__requires_session'] = AuthnSession
        return f
    return wrapper


def new_session(handler):
    handler.__annotations__['__new_session'] = True
    return handler
