from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from datetime import datetime

from vocal.api.storage.record import ArticleRecord
from vocal.constants import ArticleStatus, UserRole

from .base import define_view, ViewModel


@dataclass
@define_view('author', 'article_id', 'version_key', 'status', 'title', 'excerpt',
             'document', 'text', 'created_at', name='public')
class Article(ViewModel):
    @dataclass
    @define_view('profile_id', 'display_name', name='public')
    class _author(ViewModel):
        profile_id: UUID
        display_name: str
        role: UserRole
        created_at: datetime

    author: _author
    article_id: UUID
    version_key: UUID
    status: ArticleStatus
    title: Optional[str]
    excerpt: dict
    document: dict
    text: str
    created_at: datetime

    @classmethod
    def unmarshal_record(cls, rec: ArticleRecord) -> 'Article':
        author = cls._author(profile_id=rec.author_profile_id,
                             display_name=rec.author_display_name,
                             role=rec.author_role,
                             created_at=rec.created_at)
        return Article(article_id=rec.article_id,
                       version_key=rec.version_key,
                       status=rec.status,
                       title=rec.title,
                       excerpt=rec.excerpt,
                       document=rec.document,
                       text=rec.text,
                       created_at=rec.created_at,
                       author=author)
