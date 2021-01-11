"""add content schema

Revision ID: 4bf45a8d12ce
Revises: 4270a72b5b49
Create Date: 2021-01-01 17:29:42.800602

"""
from functools import partial

from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer, String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID


from vocal.constants import ArticleStatus
import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = '4bf45a8d12ce'
down_revision = '4270a72b5b49'
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())
v4_uuid = f.gen_random_uuid()
v1_uuid = f.uuid_generate_v1mc()
Enum = partial(Enum, values_callable=lambda en: [e.value for e in en], create_type=False)

article_status = Enum(ArticleStatus, name='article_status')


def upgrade():
    op.create_extension('uuid-ossp')
    article_status.create(op.get_bind())

    op.create_table(
        'article',
        Column('article_id', UUID(), primary_key=True, server_default=v4_uuid),
        Column('version_key', UUID, primary_key=True, server_default=v1_uuid),
        Column('author_id', UUID, ForeignKey('user_profile.user_profile_id')),
        Column('status', article_status, nullable=False),
        Column('title', String),
        Column('excerpt', JSONB, nullable=False),
        Column('document', JSONB, nullable=False),
        Column('text', String, nullable=False),
        Column('created_at', DateTime, nullable=False, server_default=utcnow))


def downgrade():
    op.drop_table('article')
    article_status.drop(op.get_bind())
    op.drop_extension('uuid-ossp')
