import asyncio
from aiohttp.cookiejar import CookieJar
from importlib import import_module
from pathlib import Path
from unittest import TestCase

import alembic.config
import sqlalchemy
from aiohttp.test_utils import AioHTTPTestCase, TestClient, setup_test_loop

import vocal.api.app
import vocal.config as config
import vocal.log
from vocal.util.asyncio import synchronously


class AsyncTestCase(type(TestCase)):
    def __new__(mcls, name, bases, ns):
        for attrname, attr in ns.items():
            if (attrname.startswith('test_') and asyncio.iscoroutinefunction(attr)):
                ns[attrname] = synchronously(attr)

        return super().__new__(mcls, name, bases, ns)


class BaseTestCase(AioHTTPTestCase, metaclass=AsyncTestCase):
    appctx = None

    def setUp(self):
        self.loop = setup_test_loop()

        self.loop.run_until_complete(self.setUpAsync())
        self.app = self.loop.run_until_complete(self.get_application())
        self.server = self.loop.run_until_complete(self.get_server(self.app))
        self.client = self.loop.run_until_complete(self.get_client(self.server))

        self.loop.run_until_complete(self.client.start_server())

    async def setUpAsync(self):
        cf = await config.load_config('config/vocal.api', 'test')
        appctx = config.AppConfig('debug', 'config', 'module')

        appctx.config.set(cf)
        appctx.module.set(vocal.api.app)

        appctx.debug.set(True)
        assert appctx.ready

        self.appctx = appctx

    async def get_application(self):
        await vocal.log.configure(self.appctx)

        mod = self.appctx.module.get()
        await mod.configure(self.appctx)

        return await mod.initialize(self.appctx)

    async def get_client(self, server):
        self.cookie_jar = CookieJar(unsafe=True)
        return TestClient(server, cookie_jar=self.cookie_jar)

    def has_cookie(self, cookie_name):
        return cookie_name in self.cookie_jar._cookies['127.0.0.1']

    def get_cookie(self, cookie_name):
        if not self.has_cookie(cookie_name):
            raise KeyError(cookie_name)
        return self.cookie_jar._cookies['127.0.0.1'][cookie_name]


class DatabaseTestCase(BaseTestCase):
    async def setUpAsync(self):
        await super().setUpAsync()
        self.appctx.declare('alembic_conf')

        config = self.appctx.config.get()
        dbconf = config['storage']

        connargs = dbconf['connection']
        connargs.update(config['secrets']['storage'])
        dsn = sqlalchemy.engine.url.URL.create('postgresql', **connargs)

        # we have to escape ourselves, instead of letting user escape in the conf
        # because create_async_engine does its own escaping (maybe?)
        esc = str(dsn).replace('%', '%%')

        base_path = Path(vocal.__file__).parent

        alconf = alembic.config.Config()
        alconf.set_main_option('script_location', str(base_path / 'migrations'))
        alconf.set_section_option('alembic', 'sqlalchemy.url', esc)
        alconf.set_section_option('alembic', 'file_template', '%%(slug)s-%%(rev)s')

        self.appctx.alembic_conf.set(alconf)
        assert self.appctx.ready
        alembic.command.upgrade(alconf, 'head')

    def tearDown(self):
        alconf = self.appctx.alembic_conf.get()
        alembic.command.downgrade(alconf, 'base')
