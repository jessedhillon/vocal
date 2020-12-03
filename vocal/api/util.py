import math
import random
from http import HTTPStatus
from functools import wraps

from aiohttp.web import Response, json_response, middleware
from aiohttp.web_exceptions import HTTPException

from vocal.api.models.base import ViewModel
from vocal.api.storage.record import BaseRecord, Recordset
from vocal.util import json


def message(handler):
    @wraps(handler)
    async def f(*args, **kwargs):
        try:
            resp = await handler(*args, **kwargs)
        except HTTPException as e:
            if e.empty_body:
                raise
            resp = e
        except ValueError as e:
            resp = e

        if isinstance(resp, (type(None), list, dict, str, ViewModel)):
            return {
                'status': {
                    'success': True,
                    'message': HTTPStatus(200).phrase,
                    'errors': [],
                },
                'data': resp,
            }
        elif isinstance(resp, (Response, HTTPException)) or isinstance(resp, tuple):
            if isinstance(resp, tuple):
                resp, obj = resp
            else:
                obj = None

            errors = []
            if obj is None:
                if isinstance(resp, HTTPException):
                    errors.append(resp.text)
                    if not isinstance(resp.body, (str, bytes)):
                        obj = resp.body
                else:
                    obj = resp.body or resp.data
            phrase = HTTPStatus(resp.status)
            success = 200 <= resp.status < 300
            body = {
                'status': {
                    'success': success,
                    'message': resp.reason,
                    'errors': errors,
                },
                'data': obj,
            }
            resp.headers.pop('Content-Type')
            return json_response(body,
                                 status=resp.status,
                                 reason=resp.reason,
                                 dumps=json.encode,
                                 headers=resp.headers)
        elif isinstance(resp, ValueError):
            reason = "Validation Failed"
            body = {
                'status': {
                    'success': False,
                    'message': reason,
                    'errors': [str(resp)]
                }
            }
            return json_response(body, status=400, reason=reason, dumps=json.encode)
        else:
            return json_response({
                    'status': {
                        'success': False,
                        'message': "unknown response type",
                        'errors': [],
                    },
                    'data': None
                },
                status=500)
    return f


@middleware
async def message_middleware(request, handler):
    wrapper = message(handler)
    return await wrapper(request)


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
        self._returning = None

    async def execute(self, session):
        if self._executed:
            raise RuntimeError("attempted double execution of operation")
        self._executed = True
        rs = await self._impl(session, *self._args, **self._kwargs)
        if self._returning is None:
            return rs
        if isinstance(rs, BaseRecord):
            return self._returning.unmarshal_record(rs)
        return self._returning.unmarshal_recordset(rs)

    def returning(self, rcls: type) -> 'operation_impl':
        self._returning = rcls
        return self

    def __repr__(self):
        return f"<operation {self._impl.__name__} *{self._args}, **{self._kwargs}>"


def generate_otp(n=6):
    return ''.join([random.choice("0123456789") for i in range(n)])


def mask_email(e):
    "https://stackoverflow.com/questions/52408105/masking-part-of-a-string/52408187"
    un, domain = e.split('@')
    mask_n = len(un) - 1
    return f"{un[0]}{'*' * mask_n}@{domain}"


def mask_phone_number(p):
    mask_n = len(p) - 8
    return f"{p[0:8]}{'*' * mask_n}"
