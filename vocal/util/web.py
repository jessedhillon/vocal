import json
from functools import wraps, partial

import aiohttp_session
import aiohttp.web as web

from .json import JsonEncoder
from vocal.api.message import ResultMessage


def json_response(handler=None, encoder_cls=JsonEncoder):
    if handler is None:
        return partial(json_response, encoder_cls=encoder_cls)

    def encode(obj):
        return json.dumps(obj, cls=encoder_cls)

    @wraps(handler)
    async def f(*args, **kwargs):
        resp = await handler(*args, **kwargs)
        if isinstance(resp, web.Response):
            return resp
        else:
            return web.json_response(resp, status=200, dumps=encode)
    return f


@web.middleware
async def json_response_middleware(request, handler):
    wrapper = json_response(handler)
    return await wrapper(request)
