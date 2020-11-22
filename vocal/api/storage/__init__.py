import sqlalchemy
import sqlalchemy.ext.asyncio


async def configure(appctx):
    appctx.declare('storage')

    config = appctx.config.get()
    dbconf = config['storage']

    connargs = dbconf['connection']
    connargs.update(config['secrets']['storage'])
    dsn = sqlalchemy.engine.url.URL.create('postgresql+asyncpg', **connargs)

    engine = sqlalchemy.ext.asyncio.create_async_engine(dsn)
    appctx.storage.set(engine)
