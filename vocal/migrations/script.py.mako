"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Boolean, DateTime, Integer, String, func as f
from sqlalchemy.dialects.postgresql import ENUM as Enum, JSONB, UUID
${imports if imports else ""}

import vocal.util.sqlalchemy


# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

utcnow = f.timezone('UTC', f.now())
v4_uuid = f.gen_random_uuid()


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
