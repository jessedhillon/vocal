import json

import vocal.api.operations as op
from vocal.api.models import user_profile

from . import DatabaseTestCase


class UsersViewTestCase(DatabaseTestCase):
    async def test_verify_email_contact_method(self):
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

        body = {
            'principalName': 'jesse@dhillon.com',
            'principalType': 'email',
        }
        resp = await self.client.request('POST', '/authn/session', json=body)
        assert resp.status == 200

        resp = await self.client.request(
                'GET',
                f'/users/{profile.user_profile_id}/contactMethods/{profile.email_contact_method_id}/verify')
        j = await resp.json()
        assert resp.status == 200
        assert j['data']['hint'] == 'j****@dhillon.com'

        sessj = self.get_cookie('TEST_SESSION').value
        sess = json.loads(sessj)['session']
        vc = sess['verify_challenge']

        vcresp = {
            'challenge_id': vc['challenge_id'],
            'passcode': vc['secret']
        }
        resp = await self.client.request(
                'POST',
                f'/users/{profile.user_profile_id}/contactMethods/{profile.email_contact_method_id}/verify',
                json=vcresp)
        assert resp.status == 200

        sessj = self.get_cookie('TEST_SESSION').value
        sess = json.loads(sessj)['session']
        assert 'verify_challenge' not in sess

        async with op.session(self.appctx) as session:
            cm = await op.user_profile.\
                    get_contact_method(profile.email_contact_method_id,
                                       user_profile_id=profile.user_profile_id).\
                    execute(session)
            assert cm.verified
