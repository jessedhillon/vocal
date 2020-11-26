"""add user role

Revision ID: aa4168fa63a9
Revises: 221c3b472f5c
Create Date: 2020-11-20 10:48:52.077951

"""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer,\
        String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID


import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = 'aa4168fa63a9'
down_revision = '221c3b472f5c'
branch_labels = None
depends_on = None

utcnow = f.timezone('UTC', f.now())

user_role = Enum('superuser', 'manager', 'creator', 'member', 'subscriber', name='user_role',
                 create_type=False)


def upgrade():
    user_role.create(op.get_bind())

    op.add_column(
        'user_profile',
        Column('role', user_role, nullable=False, server_default='subscriber'))
    op.alter_column('user_profile', 'role', server_default=None)


def downgrade():
    op.drop_column('user_profile', 'role')
    user_role.drop(op.get_bind())
