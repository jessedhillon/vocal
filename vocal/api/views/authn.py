from cryptography.fernet import Fernet
from uuid import uuid4

from aiohttp.web import HTTPUnauthorized, Response, json_response

from vocal.util.web import with_context, with_session, json_response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.models.authn import AuthnSession, AuthnChallenge, AuthnChallengeType
from vocal.api.models.user_profile import UserRole
from vocal.api.security import Capabilities as caps


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
                                 require_challenges=challenge_types, active_challenge_id=None)

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
    async with op.session(ctx) as ss:
        authn_session = AuthnSession(**session['authn_session'])
        u = await op.user_profile.\
            get_user_profile(user_profile_id=authn_session.user_profile_id).\
            execute(ss)

        if authn_session.require_challenges:
            chtype = authn_session.require_challenges.pop(0)

            if chtype is AuthnChallengeType.Email:
                secret = util.generate_otp()
                hint = util.mask_email(u.email_address)
                if u.email_contact_method_verified:
                    pass
                    # TODO: deliver challenge
                else:
                    raise ValueError(f"email {hint} must be verified first")

            elif chtype is AuthnChallengeType.SMS:
                secret = util.generate_otp()
                hint = util.mask_email(u.phone_number)
                if u.phone_contact_method_verified:
                    # TODO: deliver challenge
                    pass
                else:
                    raise ValueError("phone {hint} must be verified first")

            elif chtype is AuthnChallengeType.Password:
                secret = None
                hint = None

            challenge_id = uuid4()
            challenge = AuthnChallenge(challenge_id=challenge_id, challenge_type=chtype,
                                       hint=hint, secret=secret)
            authn_session.active_challenge_id = challenge.challenge_id
            session['authn_session'] = authn_session
            session['authn_challenge'] = challenge
            session.changed()

            return challenge.get_view('public')
