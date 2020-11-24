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
