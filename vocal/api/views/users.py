from uuid import uuid4, UUID

from aiohttp.web import HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPOk

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.constants import AuthnChallengeType, ContactMethodType
from vocal.api.models.authn import AuthnChallenge, AuthnChallengeResponse, AuthnSession
from vocal.api.models.requests import AuthnChallengeResponseRequest
from vocal.api.security import Capabilities as caps
from vocal.util.web import with_context, with_session, json_response


@json_response
@util.message
@with_session
@with_context
@security.requires(caps.Authenticate)
async def get_contact_method_verify_challenge(request, session, ctx):
    try:
        user_profile_id = UUID(request.match_info['user_profile_id'])
        contact_method_id = UUID(request.match_info['contact_method_id'])
    except ValueError:
        raise HTTPNotFound()

    if user_profile_id != session.user_profile_id:
        raise HTTPForbidden()

    async with op.session(ctx) as ss:
        cm = await op.user_profile.\
            get_contact_method(contact_method_id, user_profile_id=user_profile_id).\
            execute(ss)

        if cm.verified:
            raise ValueError("contact method is already verified")

        if cm.contact_method_type is ContactMethodType.Email:
            # TODO: deliver challenge
            chtype = AuthnChallengeType.Email

        elif cm.contact_method_type is ContactMethodType.Phone:
            # TODO: deliver challenge
            chtype = AuthnChallengeType.SMS

        session.require_challenge(chtype)
        session.next_challenge_for_contact_method(cm)
        return session.pending_challenge.get_view('public')


@json_response
@util.message
@with_session
@with_context
@security.requires(caps.Authenticate)
async def verify_contact_method(request, session, ctx):
    try:
        user_profile_id = UUID(request.match_info['user_profile_id'])
        contact_method_id = UUID(request.match_info['contact_method_id'])
    except ValueError:
        raise HTTPNotFound()

    challenge_response = AuthnChallengeResponseRequest.unmarshal_request(await request.json())

    if user_profile_id != session.user_profile_id:
        raise HTTPForbidden()

    if challenge_response.challenge_id != session.pending_challenge.challenge_id:
        raise HTTPBadRequest()

    session.pending_challenge.attempts += 1
    session.changed()
    if session.pending_challenge.attempts > security.MaxVerificationChallengeAttempts:
        session.invalidate()
        raise HTTPForbidden(body="Too many invalid attempts")

    if challenge_response.passcode != session.pending_challenge.secret:
        raise HTTPUnauthorized(body="Incorrect passcode")

    async with op.session(ctx) as ss:
        await op.user_profile.\
            mark_contact_method_verified(contact_method_id, user_profile_id=user_profile_id).\
            execute(ss)

    session.clear_pending_challenge()
    return HTTPOk()
