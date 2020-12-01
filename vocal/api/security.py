from enum import Enum
from functools import wraps

import aiohttp_session
from aiohttp.web_exceptions import HTTPForbidden

from vocal.api.constants import UserRole


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
