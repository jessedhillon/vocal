import json

import vocal.api.operations as op
from vocal.api.models import user_profile
from vocal.api.security import Capabilities as caps, _as_values

from . import DatabaseTestCase


class AuthnTestCase(DatabaseTestCase):
    async def test_start_session(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                user_profile.UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234').execute(session)

        body = {
            'principalName': 'jesse@dhillon.com',
            'principalType': 'email',
        }
        resp = await self.client.request('POST', '/authn/session', json=body)
        j = await resp.json()

        assert 'session_id' in j['data']
        assert len(j['data'].keys()) == 1

        assert 'TEST_SESSION' in resp.cookies
        session = json.loads(resp.cookies['TEST_SESSION'].value).get('session', {})

        assert 'capabilities' in session
        assert set(session['capabilities']) == set(_as_values([caps.Authenticate]))

    async def test_cannot_get_authn_challenge_with_unverified_email(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                user_profile.UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234').execute(session)

        body = {
            'principalName': 'jesse@dhillon.com',
            'principalType': 'email',
        }
        resp = await self.client.request('POST', '/authn/session', json=body)
        cookie = json.loads(self.cookie_jar._cookies['127.0.0.1']['TEST_SESSION'].value)
        session = cookie['session']
        authn_session = session['authn_session']

        resp = await self.client.request('GET', '/authn/challenge')
        j = await resp.json()
        assert resp.status == 400
        assert "email j****@dhillon.com must be verified first" in j['status']['errors']

    async def test_get_authn_challenge(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.\
                create_user_profile('Jesse',
                                    'Jesse Dhillon',
                                    '123foobar^#@',
                                    user_profile.UserRole.Subscriber,
                                    'jesse@dhillon.com',
                                    '+14155551234').\
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

        cookie = json.loads(self.get_cookie('TEST_SESSION').value)
        session = cookie['session']
        assert 'authn_challenge' in session

        challenge = session['authn_challenge']
        chresp = {
            'challenge_id': challenge['challenge_id'],
            'passcode': challenge['secret'],
        }
        resp = await self.client.request('POST', '/authn/challenge',
                                         json={**chresp, 'passcode': 'foobar'})
        assert resp.status == 401
        j = await resp.json()
        assert not j['status']['success']
        assert 'Incorrect passcode' in j['status']['errors']

        cookie = json.loads(self.get_cookie('TEST_SESSION').value)
        challenge = cookie['session']['authn_challenge']
        assert challenge['attempts'] == 1

        resp = await self.client.request('POST', '/authn/challenge', json=chresp)
        cookie = json.loads(self.get_cookie('TEST_SESSION').value)
        session = cookie['session']
        assert set(session['capabilities']) == set(['profile.list'])
        assert resp.status == 200

        resp = await self.client.request('POST', '/authn/challenge', json=chresp)
        assert resp.status == 403
