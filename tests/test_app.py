from aiohttp.test_utils import unittest_run_loop as run_loop

from . import BaseTestCase


class TestCase(BaseTestCase):
    @run_loop
    async def test_app(self):
        "tests only that the app is mounted, handles requests, produces a response"
        resp = await self.client.request('GET', '/')
        assert resp.status == 404
