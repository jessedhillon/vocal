from http import HTTPStatus
from functools import wraps

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPException


def message(handler):
    @wraps(handler)
    async def f(*args, **kwargs):
        try:
            resp = await handler(*args, **kwargs)
        except HTTPException as e:
            if e.empty_body:
                raise
            resp = e

        if isinstance(resp, (list, dict, str)):
            return {
                'status': {
                    'success': True,
                    'message': HTTPStatus(200).phrase,
                    'errors': [],
                },
                'data': resp,
            }
        elif isinstance(resp, Response):
            obj = resp.body or resp.data
            phrase = HTTPStatus(resp.status)
            success = 200 <= resp.status < 300
            resp.body = {
                'status': {
                    'success': success,
                    'message': phrase,
                    'errors': [],
                },
                'data': obj,
            }
            return resp
        elif isinstance(resp, HTTPException):
            success = 200 <= resp.status < 300
            body = {
                'status': {
                    'success': success,
                    'message': resp.reason,
                    'errors': [],
                },
                data: resp.text,
            }
            return Response(body=body,
                            status=resp.status,
                            reason=resp.reason,
                            headers=resp.headers)
    return f
