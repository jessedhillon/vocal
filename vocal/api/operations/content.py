from typing import Optional
from uuid import UUID

from sqlalchemy import func as f
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import alias, cte, exists, false, join, literal, select, true

from vocal.api.storage.sql import article, user_profile
from vocal.api.storage.record import Recordset, ArticleRecord
from vocal.api.util import operation
from vocal.constants import ArticleStatus


@operation
async def create_article(session: AsyncSession, author_id: UUID,
                         excerpt: dict, document: dict, text: str,
                         title: str, status: ArticleStatus=ArticleStatus.Draft,
                         ) -> tuple[UUID, UUID]:
    r = await session.execute(
        article.
        insert().
        values(author_id=author_id,
               status=status,
               title=title,
               excerpt=excerpt,
               document=document,
               text=text).
        returning(article.c.article_id, article.c.version_key))
    article_id, version_key = r.one()
    return article_id, version_key


@operation(record_cls=ArticleRecord, single_result=True)
async def get_article(session: AsyncSession, article_id: UUID,
                      version_key: Optional[UUID]=None
                      ) -> Result:
    q = select(article.c.article_id,
               article.c.version_key,
               article.c.status,
               article.c.title,
               article.c.excerpt,
               article.c.document,
               article.c.text,
               article.c.created_at,
               user_profile.c.user_profile_id,
               user_profile.c.display_name,
               user_profile.c.role,
               user_profile.c.created_at).\
        select_from(article).\
        join(user_profile,
             article.c.author_id == user_profile.c.user_profile_id).\
        where(article.c.article_id == article_id)

    if version_key is None:
        return await session.execute(q.order_by(article.c.version_key.desc()).limit(1))

    return await session.execute(q.where(article.c.version_key == version_key))


@operation
async def update_article(session: AsyncSession, article_id: UUID, version_key: UUID,
                         author_id: UUID, excerpt: dict, document: dict, text: str, title: str,
                         status: ArticleStatus
                         ) -> UUID:
    q = select(article.c.article_id,
               article.c.version_key).\
        select_from(article).\
        order_by(article.c.version_key.desc()).\
        limit(1)
    latest = cte(q)
    version_latest = exists().\
        select_from(latest).\
        where(latest.c.article_id == article_id).\
        where(latest.c.version_key == version_key)
    # q = select(literal(True)).with_for_update().select_from(article).where(version_latest)
    q = select(literal(True)).select_from(latest).where(version_latest)
    result = await session.execute(q)
    ex = result.scalar()
    if not ex:
        raise RuntimeError(f"attempted to insert over stale version {version_key}")

    r = await session.execute(
        article.
        insert().
        values(article_id=article_id,
               author_id=author_id,
               status=status,
               title=title,
               excerpt=excerpt,
               document=document,
               text=text).
        returning(article.c.version_key))
    return r.scalar()
