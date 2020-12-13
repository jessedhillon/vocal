import dataclasses
from collections.abc import Sequence
from enum import Enum
from typing import Callable, Generic, TypeVar
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
    def unmarshal_recordset(cls, recs: list[BaseRecord]) -> 'model_collection[ViewModel]':
        return model_collection([cls.unmarshal_record(rec) for rec in recs])

    @classmethod
    def unmarshal_record(cls, rec: BaseRecord) -> 'ViewModel':
        raise NotImplementedError()


T = TypeVar('T')
class model_collection(Sequence, Generic[T]):
    def __init__(self, objs: list[T]=None):
        self._objs = objs or []

    def __len__(self):
        return self._objs.__len__()

    def __getitem__(self, index):
        return self._objs.__getitem__(index)

    def append(self, obj: ViewModel):
        self._objs.append(obj)

    def find(self, keyf: Callable[[ViewModel], bool]=None, **kwargs):
        if keyf is not None:
            for obj in self._objs:
                if keyf(obj):
                    return obj
            return None

        elif kwargs:
            for obj in self._objs:
                match = False
                for key, val in kwargs.items():
                    match = (getattr(obj, key) == val)
                if match:
                    return obj

        raise RuntimeError("find() must be called with key function or kwargs")

    def find_all(self, keyf: Callable[[ViewModel], bool]=None, **kwargs):
        results = []
        if keyf is not None:
            for obj in self._objs:
                if keyf(obj):
                    results.append(obj)
            return results

        elif kwargs:
            for obj in self._objs:
                match = False
                for key, val in kwargs.items():
                    match = (getattr(obj, key) == val)
                if match:
                    results.append(obj)
            return results

        raise RuntimeError("find() must be called with key function or kwargs")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._objs}>"


def define_view(*fields: str, name: str):
    def f(cls):
        if not hasattr(cls, '__views__'):
            cls.__views__ = {}
        cls.__views__[name] = fields
        return cls
    return f
