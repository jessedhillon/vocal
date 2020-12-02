import aioredis
import aiohttp_session
from aiohttp.web import Application

import vocal.util as util
from vocal.api.security import RedisStorage, SimpleCookieStorage

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

    await routes.configure(appctx)
    assert appctx.ready


async def initialize(appctx):
    app = Application()
    app.add_routes(appctx.routes.get())
    aiohttp_session.setup(app, appctx.session_store.get())
    app['appctx'] = appctx
    return app
