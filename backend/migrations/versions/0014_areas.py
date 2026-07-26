"""areas + usuario_area + documento_area (Fase B.5: acceso por áreas dentro de la empresa)

Revision ID: 0014_areas
Revises: 0013_usuarios_auth
Create Date: 2026-07-26

Backfill: un área "General" por empresa, con TODOS sus documentos y usuarios dentro, para
no romper el acceso existente (todos siguen viendo todo hasta que se creen áreas reales y
se reasigne).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0014_areas"
down_revision: Union[str, None] = "0013_usuarios_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("empresa_id", "nombre", name="uq_areas_empresa_nombre"),
    )
    op.create_index("ix_areas_empresa_id", "areas", ["empresa_id"])

    op.create_table(
        "usuario_area",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usuario_id", "area_id"),
    )

    op.create_table(
        "documento_area",
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["documento_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("documento_id", "area_id"),
    )

    # Backfill: área "General" por empresa + todos los docs y usuarios dentro.
    op.execute("INSERT INTO areas (empresa_id, nombre) SELECT id, 'General' FROM empresas")
    op.execute(
        """
        INSERT INTO documento_area (documento_id, area_id)
        SELECT d.id, a.id FROM documents d
        JOIN areas a ON a.empresa_id = d.empresa_id AND a.nombre = 'General'
        """
    )
    op.execute(
        """
        INSERT INTO usuario_area (usuario_id, area_id)
        SELECT u.id, a.id FROM usuarios u
        JOIN areas a ON a.empresa_id = u.empresa_id AND a.nombre = 'General'
        WHERE u.empresa_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("documento_area")
    op.drop_table("usuario_area")
    op.drop_table("areas")
