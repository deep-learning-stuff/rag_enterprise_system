"""conversaciones + mensajes (Fase C: chat persistente)

Revision ID: 0015_conversaciones
Revises: 0014_areas
Create Date: 2026-07-26

Sin backfill: es una funcionalidad nueva, no hay datos previos que migrar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0015_conversaciones"
down_revision: Union[str, None] = "0014_areas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("creada", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "actualizada", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_conversaciones_empresa_id", "conversaciones", ["empresa_id"]
    )
    op.create_index(
        "ix_conversaciones_usuario_id", "conversaciones", ["usuario_id"]
    )

    op.create_table(
        "mensajes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversacion_id", sa.Integer(), nullable=False),
        sa.Column("rol", sa.String(length=16), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("consulta_resuelta", sa.Text(), nullable=True),
        sa.Column("answered", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("citas", sa.JSON(), nullable=True),
        sa.Column("creado", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["conversacion_id"], ["conversaciones.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_mensajes_conversacion_id", "mensajes", ["conversacion_id"])


def downgrade() -> None:
    op.drop_table("mensajes")
    op.drop_table("conversaciones")
