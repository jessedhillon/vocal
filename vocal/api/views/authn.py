from aiohttp.web import HTTPAccepted, HTTPBadRequest, HTTPOk, HTTPUnauthorized, Response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.config import AppConfig
from vocal.api.models.authn import AuthnChallenge, AuthnChallengeResponse
from vocal.api.models.requests import AuthnChallengeResponseRequest, InitiateAuthnSessionRequest
from vocal.api.security import AuthnSession, Capability
from vocal.constants import AuthnChallengeType, AuthnPrincipalType, UserRole


@security.new_session
async def init_authn_session(request, ctx: AppConfig, session: AuthnSession):
    sr = InitiateAuthnSessionRequest.unmarshal_request(await request.json())

    async with op.session(ctx) as ss:
        if sr.principal_type is AuthnPrincipalType.Email:
            u = await op.user_profile.get_user_profile(email_address=sr.principal_name).execute(ss)
            session.require_challenge(AuthnChallengeType.Email)
        elif sr.principal_type is AuthnPrincipalType.Phone:
            u = await op.user_profile.get_user_profile(phone_number=sr.principal_name).execute(ss)
            session.require_challenge(AuthnChallengeType.SMS)
        else:
            raise ValueError(sr.principal_type)

        if u is None:
            raise HTTPUnauthorized()

        session.user_profile_id = u.user_profile_id
        if u.role in {UserRole.Superuser, UserRole.Manager, UserRole.Creator}:
            session.require_challenge(AuthnChallengeType.Password)

    session.add_capabilities(Capability.Authenticate)
    return HTTPOk()


@security.requires(Capability.Authenticate)
async def get_authn_challenge(request, ctx: AppConfig, session: AuthnSession):
    if session.pending_challenge:
        raise HTTPBadRequest("cannot request a new challenge while challenges are pending")

    async with op.session(ctx) as ss:
        u = await op.user_profile.\
            get_user_profile(user_profile_id=session.user_profile_id).\
            execute(ss)

        if session.required_challenges:
            session.next_challenge_for_user(u)
            return session.pending_challenge.get_view('public')


@security.requires(Capability.Authenticate)
async def verify_authn_challenge(request, ctx: AppConfig, session: AuthnSession):
    if not session.pending_challenge:
        raise HTTPBadRequest()

    challenge_response =\
        AuthnChallengeResponseRequest.unmarshal_request(await request.json())

    if challenge_response.challenge_id != session.pending_challenge.challenge_id:
        raise ValueError("invalid challenge")

    session.pending_challenge.attempts += 1
    session.changed()
    if session.pending_challenge.attempts > security.MaxVerificationChallengeAttempts:
        session.invalidate()
        raise HTTPForbidden(text="Too many invalid attempts")

    otp_types = [AuthnChallengeType.Email, AuthnChallengeType.SMS]
    if session.pending_challenge.challenge_type in otp_types:
        if challenge_response.passcode != session.pending_challenge.secret:
            raise HTTPUnauthorized(text="Incorrect passcode")
    elif session.pending_challenge.challenge_type is AuthnChallengeType.Password:
        async with op.session(ctx) as ss:
            result = await op.authn.\
                authenticate_user(
                    user_profile_id=session.user_profile_id,
                    password=challenge_response.passcode).\
                execute(ss)
            if not result:
                raise HTTPUnauthorized(text="Incorrect passcode")
    else:
        raise HTTPBadRequest()

    session.clear_pending_challenge()
    async with op.session(ctx) as ss:
        u = await op.user_profile.\
            get_user_profile(user_profile_id=session.user_profile_id).\
            execute(ss)
    if session.required_challenges:
        session.next_challenge_for_user(u)
        return HTTPAccepted(), session.pending_challenge.get_view('public')

    session.authenticated = True
    session.set_role(u.role)
    session.remove_capabilities(Capability.Authenticate)
    return HTTPOk()
