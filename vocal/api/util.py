from http import HTTPStatus
from functools import partial, wraps

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


def operation(impl):
    @wraps(impl)
    def f(*args, **kwargs):
        return operation_impl(impl, *args, **kwargs)

    return f


class operation_impl(object):
    def __init__(self, impl, *args, **kwargs):
        self._impl = impl
        self._args = args
        self._kwargs = kwargs
        self._executed = False

    def execute(self, session):
        if self._executed:
            raise RuntimeError("attempted double execution of operation")
        self._executed = True
        return self._impl(session, *self._args, **self._kwargs)

    def __repr__(self):
        return f"<operation {self._impl.__name__} *{self._args}, **{self._kwargs}>"
