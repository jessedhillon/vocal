import math
import random
from http import HTTPStatus
from functools import wraps, partial

from aiohttp.web import Response, json_response, middleware
from aiohttp.web_exceptions import HTTPException
from sqlalchemy.engine.result import Result

from vocal.api.message import ErrorMessage, MessageStatus, ResultMessage, ScalarResultMessage,\
        VectorResultMessage, PagedResultMessage
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

        if isinstance(resp, (type(None), str, ViewModel)):
            status = MessageStatus(success=True, message=HTTPStatus(200).phrase)
            return ScalarResultMessage(status=status, data=resp)
        elif isinstance(resp, (list, dict)):
            status = MessageStatus(success=True, message=HTTPStatus(200).phrase)
            return VectorResultMessage(status=status, data=resp)
        elif isinstance(resp, (Response, HTTPException)) or isinstance(resp, tuple):
            if isinstance(resp, tuple):
                resp, obj = resp
            else:
                obj = None

            errors = []
            if obj is None:
                if isinstance(resp, HTTPException):
                    if resp.status >= 400:
                        errors.append(ErrorMessage(message=resp.text))
                    if not isinstance(resp.body, (str, bytes)):
                        obj = resp.body
                else:
                    obj = resp.body or resp.data

            success = (200 <= resp.status < 300)
            status = MessageStatus(success=success, message=resp.reason, errors=errors)
            resp.headers.pop('Content-Type')

            if isinstance(obj, (list, dict)):
                return json_response(VectorResultMessage(status=status, data=obj),
                                     status=resp.status,
                                     reason=resp.reason,
                                     dumps=json.encode,
                                     headers=resp.headers)
            else:
                return json_response(ScalarResultMessage(status=status, data=obj),
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
            status = MessageStatus(success=False, message=reason,
                                   errors=[ErrorMessage(message=str(resp))])
            return json_response(ResultMessage(status=status), status=400,
                                 reason=reason, dumps=json.encode)
        else:
            try:
                status = MessageStatus(success=True, message=HTTPStatus(200).phrase)
                return ScalarResultMessage(status=status, data=resp)
            except Exception:
                status = MessageStatus(success=False, message="unknown response type")
                return json_response(ResultMessage(status=status), status=500, dumps=json.encode)
    return f


@middleware
async def message_middleware(request, handler):
    wrapper = message(handler)
    return await wrapper(request)


def operation(impl=None, **impl_kwargs):
    if impl is None:
        return partial(operation, **impl_kwargs)

    if isinstance(impl, type) and issubclass(impl, BaseRecord):
        impl_kwargs.update({
            'record_cls': impl,
        })
        return partial(operation, **impl_kwargs)

    @wraps(impl)
    def f(*args, **kwargs):
        return operation_impl(impl, *args, **impl_kwargs, **kwargs)

    return f


class operation_impl(object):
    def __init__(self, impl, *args, single_result=False, record_cls=None, **kwargs):
        self._impl = impl
        self._args = args
        self._kwargs = kwargs
        self._executed = False
        self._record_cls = record_cls
        self._returning_cls = None
        self._single_result = single_result

    async def execute(self, session):
        if self._executed:
            raise RuntimeError("attempted double execution of operation")
        self._executed = True

        rs = await self._impl(session, *self._args, **self._kwargs)
        if self._record_cls is not None:
            recs = self._record_cls.unmarshal_result(rs, single=self._single_result)
        else:
            recs = rs

        if self._returning_cls is None:
            return recs

        if isinstance(recs, BaseRecord):
            return self._returning_cls.unmarshal_record(recs)
        elif isinstance(recs, Recordset):
            recset = self._returning_cls.unmarshal_recordset(recs)
            if self._single_result:
                return recset[0]
            return recset
        import pdb; pdb.set_trace()
        return rs

    def unmarshal_with(self, rcls: 'ViewModel') -> 'operation_impl':
        self._returning_cls = rcls
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
