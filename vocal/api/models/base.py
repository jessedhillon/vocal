import dataclasses
from enum import Enum
from types import GenericAlias
from uuid import UUID, uuid4

from vocal.api.storage import BaseRecord


class ViewModel(object):
    def as_dict(self):
        return dataclasses.asdict(self)

    def get_view(self, view_name: str):
        viewdef = self.__views__[view_name]
        return {k: v.get_view(view_name) if isinstance(v, ViewModel) else v
                for k, v in self.as_dict().items() if k in viewdef}

    @classmethod
    def unmarshal_recordset(cls, recs: list[BaseRecord]) -> list['ViewModel']:
        return [cls.unmarshal_record(rec) for rec in recs]

    @classmethod
    def unmarshal_record(cls, rec: BaseRecord) -> 'ViewModel':
        raise NotImplementedError()


def define_view(*fields: str, name: str):
    def f(cls):
        if not hasattr(cls, '__views__'):
            cls.__views__ = {}
        cls.__views__[name] = fields
        return cls
    return f
