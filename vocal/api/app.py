import aioredis
import aiohttp_session
from aiohttp.web import Application, Request, middleware

import vocal.payments
import vocal.util as util
from vocal.config import AppConfig
from vocal.api.security import AuthnSession, RedisStorage, SimpleCookieStorage
from vocal.api.util import message_middleware

from . import routes
from . import storage


async def configure(appctx):
    # e.g. configure storage, template renderer, etc
    await storage.configure(appctx)

    config = appctx.config.get()
    sc = config.get('session')

    if sc is not None:
        appctx.declare('session_store')
        if sc['storage'] == 'redis':
            pool = await aioredis.create_redis_pool(sc['pool'])
            appctx.session_store.set(RedisStorage(pool, cookie_name=sc.get('cookie_name'),
                                                  encoder=util.json.encode))
        elif sc['storage'] == 'simple':
            appctx.session_store.set(SimpleCookieStorage(cookie_name=sc.get('cookie_name'),
                                                         encoder=util.json.encode))
        else:
            raise ValueError(f"unsupported session storage: {sc['storage']}")

    await vocal.payments.configure(appctx)
    await routes.configure(appctx)
    assert appctx.ready


async def initialize(appctx):
    @middleware
    async def context_injection_middleware(request, handler):
        if not handler.__annotations__:
            return await handler(request)
        params = {}

        new_session = handler.__annotations__.pop('__new_session', False)
        for name, t in handler.__annotations__.items():
            if t is AppConfig:
                params[name] = appctx
            elif t is AuthnSession:
                if new_session:
                    params[name] = await aiohttp_session.new_session(request)
                else:
                    params[name] = await aiohttp_session.get_session(request)
            elif t is Request:
                continue
            elif name == 'return':
                continue
            else:
                raise RuntimeError(f"don't know how to inject {name}")

        return await handler(request, **params)

    app = Application(middlewares=[aiohttp_session.session_middleware(appctx.session_store.get()),
                                   util.web.json_response_middleware,
                                   message_middleware,
                                   context_injection_middleware])
    app.add_routes(appctx.routes.get())
    app['appctx'] = appctx

    return app
