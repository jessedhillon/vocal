import json
from importlib import import_module

import pytest
from aiohttp.test_utils import unittest_run_loop as run_loop

import vocal.api.operations as op
import vocal.api.models.user_profile as user_profile

from . import DatabaseTestCase


class UserProfileOperationsTestCase(DatabaseTestCase):
    @run_loop
    async def test_create_and_get_user_profile(self):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                user_profile.UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234').execute(session)
            rec = await op.user_profile.get_user_profile(profile_id).execute(session)

            assert rec is not None
            assert rec.user_profile_id == profile_id

            fake_uuid = '75a3cffc-641c-4779-9442-31a2995ddec3'
            rec2 = await op.user_profile.get_user_profile(fake_uuid).execute(session)
            assert rec2 is None

    @run_loop
    async def test_create_multiple_and_get_user_profile(self):
        profile_ids = await op.execute(self.appctx, [
            op.user_profile.create_user_profile(
                'Jesse',
                'Jesse Dhillon',
                '123foobar^#@',
                user_profile.UserRole.Subscriber,
                'jesse@dhillon.com',
                '+14155551234'),
            op.user_profile.create_user_profile(
                'Alice G.',
                'Alice Goodwell',
                'password123!',
                user_profile.UserRole.Subscriber,
                'alice@example.com'),
        ])
        assert all(profile_ids)
        assert len(profile_ids) == 2

        async with op.session(self.appctx) as session:
            p1 = await op.user_profile.get_user_profile(profile_ids[0]).execute(session)
            p2 = await op.user_profile.get_user_profile(profile_ids[1]).execute(session)
            assert p1.user_profile_id != p2.user_profile_id
            assert p1.display_name == 'Jesse'
            assert p2.display_name == 'Alice G.'

    @run_loop
    async def test_cannot_create_duplicate_emails(self):
        email = 'jesse@dhillon.com'
        with pytest.raises(ValueError) as excinfo:
            await op.execute(self.appctx, [
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    user_profile.UserRole.Subscriber,
                    email,
                    '+14155551234'),
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    user_profile.UserRole.Subscriber,
                    email),
            ])
        assert str(excinfo.value) == f"user profile with email {email} already exists"

    @run_loop
    async def test_cannot_create_duplicate_phone_numbers(self):
        pn = '+14155551234'
        with pytest.raises(ValueError) as excinfo:
            await op.execute(self.appctx, [
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    user_profile.UserRole.Subscriber,
                    None,
                    pn),
                op.user_profile.create_user_profile(
                    'Jesse',
                    'Jesse Dhillon',
                    '123foobar^#@',
                    user_profile.UserRole.Subscriber,
                    None,
                    pn),
            ])
        assert str(excinfo.value) == f"user profile with phone number {pn} already exists"
