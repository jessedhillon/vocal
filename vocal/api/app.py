import json

import aioredis
import aiohttp_session
from aiohttp_session.redis_storage import RedisStorage
from aiohttp.web import Application

import vocal.util as util

from .routes import routes


async def configure(config):
    # e.g. configure storage, template renderer, etc
    conf = {
        'routes': routes,
    }

    sc = config.get('session')
    if sc is not None:
        if sc['storage'] == 'redis':
            pool = await aioredis.create_pool(sc['pool'])
            conf['session_store'] = RedisStorage(pool,
                                                 cookie_name=sc.get('cookie_name'),
                                                 encoder=util.json.encode)
        else:
            raise ValueError(f"unsupported session storage: {sc['storage']}")

    return conf


async def initialize(config):
    app = Application()
    app.add_routes(config['routes'])
    aiohttp_session.setup(app, config['session_store'])
    return app
