import json

from aiohttp.test_utils import unittest_run_loop as run_loop

from vocal.api.security import Capabilities as caps, _as_values

from . import BaseTestCase


class AuthnTestCase(BaseTestCase):
    @run_loop
    async def test_start_session(self):
        resp = await self.client.request('POST', '/authn/session')
        assert 'TEST_SESSION' in resp.cookies
        session = json.loads(resp.cookies['TEST_SESSION'].value).get('session', {})

        assert 'capabilities' in session
        assert set(session['capabilities']) == set(_as_values([caps.Authenticate]))
