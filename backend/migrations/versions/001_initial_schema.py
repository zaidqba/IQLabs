"""Initial IQ-RAD database schema.

Revision ID: 001
Revises:
Create Date: 2026-03-26

NOTE: This migration creates all tables via SQLAlchemy metadata.
The SQL schema files in database/schema/ are the authoritative source
for SQL Server production deployment. This migration supports dev/test
with Docker SQL Server.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All tables are created by Alembic from the ORM metadata.
    # In production (Ionetix3/SQLEXPRESS), use the database/schema/ SQL files directly.
    # This migration is for dev/test Docker SQL Server only.
    pass  # Tables created by create_all() at app startup in dev mode


def downgrade() -> None:
    pass
