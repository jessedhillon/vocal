from uuid import uuid4

from aiohttp.web import HTTPBadRequest, HTTPForbidden

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.models.authn import AuthnChallenge, AuthnChallengeResponse, AuthnSession,\
    AuthnChallengeType
from vocal.api.models.user_profile import ContactMethodType
from vocal.api.security import Capabilities as caps
from vocal.util.web import with_context, with_session, json_response


@json_response
@util.message
@with_session
@with_context
@security.requires(caps.Authenticate)
async def get_contact_method_verify_challenge(request, session, ctx):
    user_profile_id = request.match_info['user_profile_id']
    contact_method_id = request.match_info['contact_method_id']
    authn_session = AuthnSession(**session['authn_session'])

    if user_profile_id != authn_session.user_profile_id:
        raise HTTPForbidden()

    async with op.session(ctx) as ss:
        cm = await op.user_profile.\
            get_contact_method(contact_method_id, user_profile_id=user_profile_id).\
            execute(ss)

        if cm.verified:
            raise ValueError("contact method is already verified")

        secret = util.generate_otp()
        if cm.contact_method_type is ContactMethodType.Email:
            hint = util.mask_email(cm.email_address)
            chtype = AuthnChallengeType.Email
            # TODO: deliver challenge

        elif cm.contact_method_type is ContactMethodType.Phone:
            hint = util.mask_phone_number(cm.phone_number)
            chtype = AuthnChallengeType.SMS
            # TODO: deliver challenge

        challenge_id = uuid4()
        challenge = AuthnChallenge(challenge_id=challenge_id, challenge_type=chtype,
                                   hint=hint, secret=secret)
        session['verify_challenge'] = challenge
        session.changed()

        return challenge.get_view('public')


@json_response
@util.message
@with_session
@with_context
@security.requires(caps.Authenticate)
async def verify_contact_method(request, session, ctx):
    user_profile_id = request.match_info['user_profile_id']
    contact_method_id = request.match_info['contact_method_id']
    authn_session = AuthnSession(**session['authn_session'])

    verify_challenge = AuthnChallenge(**session['verify_challenge'])
    challenge_response = AuthnChallengeResponse(**await request.json())

    if user_profile_id != authn_session.user_profile_id:
        raise HTTPForbidden()

    if challenge_response.challenge_id != verify_challenge.challenge_id:
        raise HTTPBadRequest()

    verify_challenge.attempts += 1
    session.changed()
    if verify_challenge.attempts > security.MaxVerificationChallengeAttempts:
        session.pop('verify_challenge')
        raise HTTPForbidden(body="Too many invalid attempts")

    if challenge_response.passcode != verify_challenge.secret:
        raise HTTPUnauthorized(body="Incorrect passcode")

    async with op.session(ctx) as ss:
        await op.user_profile.\
            mark_contact_method_verified(contact_method_id, user_profile_id=user_profile_id).\
            execute(ss)

    session.pop('verify_challenge')
    return
