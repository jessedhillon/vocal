import asyncio
import json
from aiohttp.cookiejar import CookieJar
from importlib import import_module
from pathlib import Path
from unittest import TestCase

import alembic.config
import sqlalchemy
from aiohttp.test_utils import AioHTTPTestCase, TestClient, setup_test_loop

import vocal.api.app
import vocal.api.operations as op
import vocal.api.storage as storage
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

    async def configure(self):
        cf = await config.load_config('config/vocal.api', 'test')
        appctx = config.AppConfig('debug', 'config', 'module')

        appctx.config.set(cf)
        appctx.module.set(vocal.api.app)

        appctx.debug.set(True)
        assert appctx.ready

        self.appctx = appctx

    async def setUpAsync(self):
        await self.configure()


class DatabaseTestCase(BaseTestCase):
    async def setUpAsync(self):
        await super().configure()
        await storage.configure(self.appctx)
        await self.migrate_head()

    async def migrate_head(self):
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


class AppTestCase(DatabaseTestCase):
    async def setUpAsync(self):
        await super().configure()

        self.app = await self.get_application()
        self.server = await self.get_server(self.app)
        self.client = await self.get_client(self.server)

        await self.migrate_head()
        await self.client.start_server()

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

    def get_session(self):
        cv = json.loads(self.get_cookie('TEST_SESSION').value)
        return cv['session']

    async def authenticate_as(self, role):
        async with op.session(self.appctx) as session:
            profile_id = await op.user_profile.\
                create_user_profile('Test',
                                    'Test User',
                                    '123foobar^#@',
                                    role,
                                    'test@example.com',
                                    '+14155551234').\
                execute(session)
            profile = await op.user_profile.\
                get_user_profile(user_profile_id=profile_id).\
                execute(session)
            await op.user_profile.\
                mark_contact_method_verified(contact_method_id=profile.email_contact_method_id).\
                execute(session)

        body = {
            'principalName': profile.email_address,
            'principalType': 'email',
        }
        await self.client.request('POST', '/authn/session', json=body)
        await self.client.request('GET', '/authn/challenge')

        cookie = json.loads(self.get_cookie('TEST_SESSION').value)
        session = cookie['session']
        challenge = session['pending_challenge']

        chresp = {
            'challenge_id': challenge['challenge_id'],
            'passcode': challenge['secret'],
        }
        resp = await self.client.request('POST', '/authn/challenge', json=chresp)

        cookie = json.loads(self.get_cookie('TEST_SESSION').value)
        session = cookie['session']
        challenge = session['pending_challenge']

        chresp = {
            'challenge_id': challenge['challenge_id'],
            'passcode': '123foobar^#@',
        }
        resp = await self.client.request('POST', '/authn/challenge', json=chresp)
