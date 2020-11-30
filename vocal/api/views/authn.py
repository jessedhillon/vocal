from uuid import uuid4

from aiohttp.web import HTTPAccepted, HTTPBadRequest, HTTPUnauthorized, Response, json_response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.models.authn import AuthnSession, AuthnChallenge, AuthnChallengeResponse,\
        AuthnChallengeType
from vocal.api.models.user_profile import UserRole
from vocal.api.security import Capabilities as caps
from vocal.util.web import with_context, with_session, json_response


@json_response
@util.message
@with_session(new=True)
@with_context
async def init_authn_session(request, session, ctx):
    body = await request.json()
    principal = body['principalName']
    principal_type = body['principalType']

    args = {}
    challenge_types = []

    if principal_type == 'email':
        args['email_address'] = principal
        challenge_types.append(AuthnChallengeType.Email)
    elif principal_type == 'phone':
        args['phone_number'] = principal
        challenge_types.append(AuthnChallengeType.SMS)

    async with op.session(ctx) as ss:
        u = await op.user_profile.get_user_profile(**args).execute(ss)

        if u is None:
            raise HTTPUnauthorized()

        if u.role in {UserRole.Superuser, UserRole.Manager, UserRole.Creator}:
            challenge_types.append(AuthnChallengeType.Password)

    sk = uuid4()
    authn_session = AuthnSession(session_id=sk, user_profile_id=u.user_profile_id,
                                 require_challenges=challenge_types)

    security.add_capabilities(session, caps.Authenticate)
    session['authn_session'] = authn_session.as_dict()
    session.changed()

    return authn_session.get_view('public')


@json_response
@util.message
@with_session
@with_context
@security.requires(caps.Authenticate)
async def get_authn_challenge(request, session, ctx):
    authn_session = AuthnSession(**session['authn_session'])
    if 'authn_challenge' in session:
        raise HTTPBadRequest()

    async with op.session(ctx) as ss:
        u = await op.user_profile.\
            get_user_profile(user_profile_id=authn_session.user_profile_id).\
            execute(ss)

        if authn_session.require_challenges:
            chtype = authn_session.require_challenges.pop(0)

            challenge = AuthnChallenge.create_challenge_for_user(u, chtype)
            session['authn_session'] = authn_session
            session['authn_challenge'] = challenge

            # TODO: deliver challenge

            return challenge.get_view('public')


@json_response
@util.message
@with_session
@with_context
@security.requires(caps.Authenticate)
async def verify_authn_challenge(request, session, ctx):
    if 'authn_challenge' not in session:
        raise HTTPBadRequest()

    authn_session = AuthnSession(**session['authn_session'])
    authn_challenge = AuthnChallenge(**session['authn_challenge'])
    challenge_response = AuthnChallengeResponse(**await request.json())

    if challenge_response.challenge_id != authn_challenge.challenge_id:
        raise HTTPBadRequest()

    authn_challenge.attempts += 1
    if authn_challenge.attempts > security.MaxVerificationChallengeAttempts:
        session.pop('authn_challenge')
        session.pop('authn_session')
        raise HTTPForbidden(text="Too many invalid attempts")

    otp_types = [AuthnChallengeType.Email, AuthnChallengeType.SMS]
    if authn_challenge.challenge_type in otp_types:
        if challenge_response.passcode != authn_challenge.secret:
            session['authn_challenge'] = authn_challenge
            raise HTTPUnauthorized(text="Incorrect passcode")
    elif authn_challenge.challenge_type is AuthnChallengeType.Password:
        # TODO: implement this
        raise NotImplementedError()
    else:
        raise HTTPBadRequest()

    session.pop('authn_challenge')
    if authn_session.require_challenges:
        async with op.session(ctx) as ss:
            u = await op.user_profile.\
                get_user_profile(user_profile_id=authn_session.user_profile_id).\
                execute(ss)

        next_chtype = authn_session.require_challenges.pop(0)
        next_challenge = AuthnChallengeResponse.create_challenge_for_user(u, next_chtype)
        session['authn_challenge'] = next_challenge
        return HTTPAccepted(text=next_challenge.get_view('public'))
    else:
        security.add_capabilities(session, caps.ProfileList)
        security.remove_capabilities(session, caps.Authenticate)
        return None
