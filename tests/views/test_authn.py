import json

import vocal.api.operations as op
from vocal.api.models import user_profile
from vocal.api.security import Capability
from vocal.constants import UserRole

from .. import AppTestCase


class AuthnTestCase(AppTestCase):
    async def test_start_session(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.\
                create_user_profile('Jesse', 'Jesse Dhillon', '123foobar^#@',
                                    UserRole.Subscriber, 'jesse@dhillon.com', '+14155551234').\
                execute(session)

        body = {
            'principalName': 'jesse@dhillon.com',
            'principalType': 'email',
        }
        resp = await self.client.request('POST', '/authn/session', json=body)
        j = await resp.json()

        assert 'TEST_SESSION' in resp.cookies
        session = self.get_session()

        assert 'capabilities' in session
        assert set(session['capabilities']) == set([Capability.Authenticate.value])

    async def test_cannot_get_authn_challenge_with_unverified_email(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234').execute(session)

        body = {
            'principalName': 'jesse@dhillon.com',
            'principalType': 'email',
        }
        await self.client.request('POST', '/authn/session', json=body)

        resp = await self.client.request('GET', '/authn/challenge')
        j = await resp.json()
        assert resp.status == 400
        assert "email j****@dhillon.com must be verified first" in\
               [e['message'] for e in j['status']['errors']]

    async def test_get_authn_challenge(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.\
                create_user_profile('Jesse', 'Jesse Dhillon', '123foobar^#@',
                                    UserRole.Subscriber, 'jesse@dhillon.com', '+14155551234').\
                execute(session)
            profile = await op.user_profile.\
                get_user_profile(user_profile_id=profile_id).\
                execute(session)
            await op.user_profile.\
                mark_contact_method_verified(contact_method_id=profile.email_contact_method_id).\
                execute(session)

        body = {
            'principalName': 'jesse@dhillon.com',
            'principalType': 'email',
        }
        await self.client.request('POST', '/authn/session', json=body)
        await self.client.request('GET', '/authn/challenge')

        session = self.get_session()
        assert session['pending_challenge'] is not None

        challenge = session['pending_challenge']
        chresp = {
            'challenge_id': challenge['challenge_id'],
            'passcode': challenge['secret'],
        }
        resp = await self.client.request('POST', '/authn/challenge',
                                         json={**chresp, 'passcode': 'foobar'})
        assert resp.status == 401
        j = await resp.json()
        assert not j['status']['success']
        assert 'Incorrect passcode' in [e['message'] for e in j['status']['errors']]

        session = self.get_session()
        challenge = session['pending_challenge']
        assert challenge['attempts'] == 1

        resp = await self.client.request('POST', '/authn/challenge', json=chresp)
        session = self.get_session()
        assert resp.status == 200
        # check that we have some expected normie permissions
        assert set(session['capabilities']) >= set(['profile.list', 'payment_method.create'])

        resp = await self.client.request('POST', '/authn/challenge', json=chresp)
        assert resp.status == 403
