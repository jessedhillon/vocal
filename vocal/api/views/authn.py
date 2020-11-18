from cryptography.fernet import Fernet

from aiohttp.web import Response, json_response

from vocal.util.web import with_session, json_response

import vocal.api.security as security
import vocal.api.util as util
from ..security import Capabilities as caps


@json_response
@util.message
@with_session(new=True)
async def init_authn_session(request, session):
    sk = Fernet.generate_key().decode('utf8')
    security.add_capabilities(session, caps.Authenticate)
    session['authn_session_key'] = sk
    return {
        'authn_session': {
            'session_key': sk,
        }
    }


@json_response
@with_session
@security.requires(caps.Authenticate)
async def get_authn_challenge(request, session):
    return {
        'text': "some_challenge",
    }
