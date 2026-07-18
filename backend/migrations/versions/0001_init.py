"""init: extensión pgvector + tabla documents

Revision ID: 0001_init
Revises:
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deja la BD lista para vectores (aún NO usamos columnas vector; solo infra).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column(
            "estado", sa.String(length=32), nullable=False, server_default="subido"
        ),
        sa.Column("storage_ref", sa.String(length=512), nullable=False),
        sa.Column(
            "fecha_subida",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("documents")
    # No borramos la extensión vector: otros objetos podrían depender de ella.
