import datetime
import decimal
import enum
import json
import uuid

import psycopg2.extras

from vocal.api.message import ResultMessage


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'marshal_dict'):
            return obj.marshal_dict()

        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, (datetime.timedelta)):
            return obj.seconds
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, psycopg2.extras.Json):
            return obj.dumps(obj.adapted)

        return json.JSONEncoder.default(self, obj)


def encode(obj):
    return json.dumps(obj, cls=JsonEncoder)
