from enum import Enum
from functools import wraps

from aiohttp.web_exceptions import HTTPForbidden


class Capabilities(Enum):
    Authenticate = 'authn'


def _as_values(caps):
    return [c.value for c in caps]


def add_capabilities(session, *caps):
    session['capabilities'] = set(session.setdefault('capabilities', [])) | set(caps)
    session.changed()


def has_capabilities(session, *caps):
    caps = _as_values(caps)
    return session.setdefault('capabilities', []) and set(session['capabilities']) <= set(caps)


def requires(*capabilities):
    def wrapper(handler):
        @wraps(handler)
        def f(request, session, *args, **kwargs):
            if not has_capabilities(session, *capabilities):
                raise HTTPForbidden()
            else:
                return handler(request, session, *args, **kwargs)
        return f
    return wrapper
