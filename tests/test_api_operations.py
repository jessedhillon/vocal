import json
from importlib import import_module

from aiohttp.test_utils import unittest_run_loop as run_loop

import vocal.api.operations as op
import vocal.api.models.user_profile as user_profile

from . import DatabaseTestCase


class ApiOperationsTestCase(DatabaseTestCase):
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
            profile = await op.user_profile.get_user_profile(profile_id).execute(session)

            assert profile is not None
            assert profile[0] == profile_id
