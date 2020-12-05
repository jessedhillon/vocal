import dataclasses
from dataclasses import dataclass, field
from typing import Generic, Optional, TypeVar


T = TypeVar('T')


@dataclass(frozen=True)
class ErrorMessage:
    message: str
    error_id: str = field(default=None)
    context: str = field(default=None)


@dataclass(frozen=True)
class MessageStatus:
    success: bool
    message: Optional[str]
    errors: list[ErrorMessage] = field(default_factory=list)


@dataclass(frozen=True)
class PaginationStatus:
    page: int
    total: int
    size: int


@dataclass(frozen=True)
class ResultMessage(Generic[T]):
    status: MessageStatus

    def marshal(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ScalarResultMessage(ResultMessage):
    data: T


@dataclass(frozen=True)
class VectorResultMessage(ResultMessage):
    data: list[T]


@dataclass(frozen=True)
class PagedResultMessage(VectorResultMessage):
    page: PaginationStatus
