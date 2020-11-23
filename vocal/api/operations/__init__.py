from contextlib import asynccontextmanager
from functools import partial, wraps

import sqlalchemy.ext.asyncio

from vocal.api.util import operation
from . import user_profile


async def execute(appctx, operations):
    results = []
    engine = appctx.storage.get()
    async with session(appctx) as s:
        for op in operations:
            results.append(await op.execute(s))
    return results


@asynccontextmanager
async def session(appctx):
    engine = appctx.storage.get()
    async with sqlalchemy.ext.asyncio.AsyncSession(engine) as s:
        async with s.begin():
            yield s
