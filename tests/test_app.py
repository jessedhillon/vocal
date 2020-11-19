import json

from aiohttp.test_utils import AioHTTPTestCase as TestCase, unittest_run_loop as run_loop

import vocal.api.app as app
import vocal.config as config
import vocal.log


class WebAppTestCase(TestCase):
    appctx = None

    async def get_application(self):
        cf = await config.load_config('config/vocal.api', 'test')
        appctx = config.AppConfig('debug', 'config', 'module')
        self.appctx = appctx

        appctx.config.set(cf)
        appctx.module.set(app)
        await vocal.log.configure(appctx)
        appctx.debug.set(True)
        assert appctx.ready

        mod = self.appctx.module.get()

        await mod.configure(self.appctx)
        return await mod.initialize(self.appctx)

    @run_loop
    async def test_app(self):
        "tests only that the app is mounted, handles requests, produces a response"
        resp = await self.client.request('GET', '/')
        assert resp.status == 404
