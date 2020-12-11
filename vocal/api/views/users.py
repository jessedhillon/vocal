from uuid import uuid4, UUID

from aiohttp.web import HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPOk, Request

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.models.authn import AuthnChallenge, AuthnChallengeResponse
from vocal.api.models.requests import AuthnChallengeResponseRequest, AddPaymentMethodRequest
from vocal.api.models.user_profile import UserProfile
from vocal.api.security import AuthnSession, Capability
from vocal.config import AppConfig
from vocal.constants import AuthnChallengeType, ContactMethodType, PaymentMethodStatus
from vocal.payments.models import PaymentCredential


@security.requires(Capability.Authenticate)
async def get_contact_method_verify_challenge(request, ctx: AppConfig, session: AuthnSession):
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


@security.requires(Capability.Authenticate)
async def verify_contact_method(request, ctx: AppConfig, session: AuthnSession):
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


@security.requires(Capability.PaymentMethodCreate)
async def add_payment_method(request, ctx: AppConfig, session: AuthnSession):
    try:
        user_profile_id = UUID(request.match_info['user_profile_id'])
    except ValueError:
        raise HTTPNotFound()

    if user_profile_id != session.user_profile_id:
        raise HTTPForbidden()

    async with op.session(ctx) as ss:
        # fail if user's email address is not verified
        u = await op.user_profile.get_user_profile(user_profile_id=user_profile_id).execute(ss)
        if not u.email_contact_method_verified:
            raise ValueError("email address must be verified first")

        addpmrq = AddPaymentMethodRequest.unmarshal_request(await request.json())
        payments = ctx.payments.get()
        processor = payments[addpmrq.processor_id]

        pp = await op.user_profile.\
            get_payment_profile(user_profile_id=user_profile_id,
                                processor_id=addpmrq.processor_id).\
            execute(ss)

        if pp is not None:
            pp_id = pp.payment_profile_id
            cust_id = pp.processor_customer_profile_id
        else:
            cust_id = await processor.create_customer_profile(
                u.user_profile_id, u.name, u.email_address, u.phone_number, address=None)
            pp_id = await op.user_profile.\
                add_payment_profile(
                    user_profile_id=u.user_profile_id,
                    processor_id=processor.processor_id,
                    processor_customer_profile_id=cust_id).\
                execute(ss)

    async with op.session(ctx) as ss:
        method_id = await processor.\
            add_customer_payment_method(cust_id, addpmrq.payment_credential)

        pm_id = await op.user_profile.\
            add_payment_method(
                user_profile_id=u.user_profile_id,
                payment_profile_id=pp_id,
                processor_payment_method_id=method_id,
                payment_method_type=addpmrq.payment_credential.method_type,
                payment_method_family=addpmrq.payment_credential.method_family,
                display_name=addpmrq.payment_credential.display_name,
                safe_account_number_fragment=\
                    addpmrq.payment_credential.safe_account_number_fragment,
                expires_after=addpmrq.payment_credential.expire_after_date).\
            execute(ss)

    return pm_id
