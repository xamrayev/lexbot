"""Compliance Center: watches, checks, notifications.

Uses metadata-based creation with checkfirst so the revision is a no-op on
fresh databases where baseline 0001 already materialized these tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-04

"""
from alembic import op

from app.db.base import Base
from app import models  # noqa: F401 — register all tables on Base.metadata

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_TABLES = ["compliance_watches", "compliance_checks", "notifications"]


def upgrade() -> None:
    bind = op.get_bind()
    tables = [Base.metadata.tables[name] for name in _TABLES]
    Base.metadata.create_all(bind=bind, tables=tables, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [Base.metadata.tables[name] for name in _TABLES]
    Base.metadata.drop_all(bind=bind, tables=tables, checkfirst=True)
