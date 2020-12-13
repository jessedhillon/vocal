import json

import vocal.api.operations as op
from vocal.api.models import user_profile
from vocal.constants import UserRole

from .. import AppTestCase


class UsersViewTestCase(AppTestCase):
    async def test_verify_email_contact_method(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.\
                create_user_profile('Jesse',
                                    'Jesse Dhillon',
                                    '123foobar^#@',
                                    UserRole.Subscriber,
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

        session = self.get_session()
        vc = session['pending_challenge']

        vcresp = {
            'challenge_id': vc['challenge_id'],
            'passcode': vc['secret']
        }
        resp = await self.client.request(
            'POST',
            f'/users/{profile.user_profile_id}/contactMethods/{profile.email_contact_method_id}/verify',
            json=vcresp)
        assert resp.status == 200

        session = self.get_session()
        assert session['pending_challenge'] is None

        async with op.session(self.appctx) as session:
            cm = await op.user_profile.\
                    get_contact_method(profile.email_contact_method_id,
                                       user_profile_id=profile.user_profile_id).\
                    execute(session)
            assert cm.verified

    async def test_add_payment_method(self):
        profile_id = await self.authenticate_as(UserRole.Subscriber)
        body = {
            'processorId': 'com.example',
            'paymentCredential': {
                'methodType': 'credit_card',
                'cardNumber': '4242424242424242',
                'expMonth': 12,
                'expYear': 2023,
                'cvv': '444',
            }
        }
        resp = await self.client.request(
            'POST',
            f'/users/{profile_id}/paymentMethods',
            json=body)
        j = await resp.json()
        pm_id = j['data']

        payments = self.appctx.payments.get()
        mock = payments['com.example']

        async with op.session(self.appctx) as ss:
            pp = await op.user_profile.get_payment_profile(
                    user_profile_id=profile_id,
                    processor_id='com.example').\
                execute(ss)
            pms = await op.user_profile.get_payment_methods(
                    user_profile_id=profile_id,
                    payment_profile_id=pp.payment_profile_id).\
                execute(ss)
        assert pp.processor_customer_profile_id in mock._customers
        for pp_id, pmeths in pms.group_by('payment_profile_id').items():
            assert pp_id == pp.payment_profile_id
            assert len(pmeths) == 1
            for pm in pmeths:
                assert str(pm.payment_method_id) == pm_id

    async def test_add_multiple_payment_method(self):
        profile_id = await self.authenticate_as(UserRole.Subscriber)
        bodies = [{
            'processorId': 'com.example',
            'paymentCredential': {
                'methodType': 'credit_card',
                'cardNumber': '4242424242424242',
                'expMonth': 12,
                'expYear': 2023,
                'cvv': '444',
            }
        },{
            'processorId': 'com.example',
            'paymentCredential': {
                'methodType': 'credit_card',
                'cardNumber': '4000056655665556',
                'expMonth': 12,
                'expYear': 2022,
                'cvv': '555',
            }
        }]

        pm_ids = []
        for b in bodies:
            resp = await self.client.request(
                'POST',
                f'/users/{profile_id}/paymentMethods',
                json=b)
            j = await resp.json()
            pm_ids.append(j['data'])

        payments = self.appctx.payments.get()
        mock = payments['com.example']

        async with op.session(self.appctx) as ss:
            pp = await op.user_profile.get_payment_profile(
                    user_profile_id=profile_id,
                    processor_id='com.example').\
                execute(ss)
            pms = await op.user_profile.get_payment_methods(
                    user_profile_id=profile_id,
                    payment_profile_id=pp.payment_profile_id).\
                execute(ss)
        assert pp.processor_customer_profile_id in mock._customers
        for pp_id, pmeths in pms.group_by('payment_profile_id').items():
            assert pp_id == pp.payment_profile_id
            assert len(pmeths) == 2
            for pm in pmeths:
                assert str(pm.payment_method_id) in pm_ids
