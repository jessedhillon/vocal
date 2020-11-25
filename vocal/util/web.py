import json
from functools import wraps, partial

import aiohttp_session
import aiohttp.web as web

from .json import JsonEncoder


def with_context(handler):
    @wraps(handler)
    async def f(request, *args, **kwargs):
        ctx = request.app['appctx']
        return await handler(request, *args, ctx, **kwargs)
    return f


def with_session(handler=None, new=False):
    if handler is None:
        return partial(with_session, new=new)

    @wraps(handler)
    async def f(request, *args, **kwargs):
        if new:
            session = await aiohttp_session.new_session(request)
        else:
            session = await aiohttp_session.get_session(request)
        return await handler(request, *args, session, **kwargs)
    return f


def json_response(handler=None, encoder_cls=JsonEncoder):
    if handler is None:
        return partial(json_response, encoder_cls=encoder_cls)

    encode = lambda obj: json.dumps(obj, cls=encoder_cls)

    @wraps(handler)
    async def f(*args, **kwargs):
        resp = await handler(*args, **kwargs)
        if isinstance(resp, (list, dict, str)):
            return web.json_response(resp, status=200, dumps=encode)
        return resp
    return f
