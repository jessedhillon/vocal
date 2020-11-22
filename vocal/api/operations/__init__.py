from functools import partial, wraps

import sqlalchemy.ext.asyncio

from vocal.api.util import operation
from . import user_profile


async def execute(appctx, operations):
    results = []
    engine = appctx.storage.get()
    async with session(appctx) as s:
        async with s.begin():
            for op in operations:
                results.append(await op.execute(s))
    return results


def session(appctx):
    engine = appctx.storage.get()
    return sqlalchemy.ext.asyncio.AsyncSession(engine)
