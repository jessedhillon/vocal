import dataclasses
from enum import Enum
from types import GenericAlias
from uuid import UUID, uuid4


class ViewModel(object):
    def as_dict(self):
        return dataclasses.asdict(self)

    def get_view(self, view_name):
        viewdef = self.__views__[view_name]
        return {k: v.get_view(view_name) if isinstance(v, ViewModel) else v
                for k, v in self.as_dict().items() if k in viewdef}

    def __post_init__(self):
        for field in dataclasses.fields(self):
            t = field.type
            v = getattr(self, field.name)

            # unmarshall enum or list[enum]
            is_list = False
            if isinstance(field.type, GenericAlias) and field.type.__origin__ is list:
                t = t.__args__[0]
                is_list = True
            if is_list:
                enum_list = []
                if issubclass(t, Enum):
                    for u in v:
                        if isinstance(u, str):
                            enum_list.append(t(u))
                        else:
                            enum_list.append(u)
                    setattr(self, field.name, enum_list)
            else:
                if issubclass(t, Enum) and isinstance(v, str):
                    setattr(self, field.name, t(v))


def define_view(*fields, name):
    def f(cls):
        if not hasattr(cls, '__views__'):
            cls.__views__ = {}
        cls.__views__[name] = fields
        return cls
    return f
