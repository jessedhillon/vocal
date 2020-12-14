from uuid import UUID

from sqlalchemy import func as f
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import alias, exists, false, join, literal, select, true

from vocal.api.util import operation
from vocal.api.storage.sql import user_auth


@operation
async def authenticate_user(session: AsyncSession, user_profile_id: UUID, password: str) -> bool:
    q = select(user_auth.c.password_crypt == f.crypt(password, user_auth.c.password_crypt)).\
        where(user_auth.c.user_profile_id == user_profile_id)
    rs = await session.execute(q)
    return rs.scalar()
