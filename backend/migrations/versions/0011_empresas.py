"""empresas (tenants): tabla + empresa_id en documents, chunks, gaps, query_logs

Revision ID: 0011_empresas
Revises: 0010_gap_recheck
Create Date: 2026-07-26

Fase A del multi-tenant. Las columnas empresa_id se crean NULLABLE a propósito: se
endurecen a NOT NULL al cerrar la Fase A (cuando la ingesta selle empresa_id). Los datos
ya existentes se asignan a una empresa "por defecto" (backfill), así nada se pierde.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011_empresas"
down_revision: Union[str, None] = "0010_gap_recheck"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tablas que ganan empresa_id. chunks se backfillea desde su documento; el resto va a la
# empresa por defecto.
_TABLAS = ("documents", "chunks", "gaps", "query_logs")


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Empresa por defecto: absorbe todos los datos ya existentes. Sin id explícito para
    # no desincronizar la secuencia serial de la tabla.
    empresas = sa.table(
        "empresas", sa.column("id", sa.Integer), sa.column("nombre", sa.String)
    )
    op.bulk_insert(empresas, [{"nombre": "Empresa por defecto"}])

    for tabla in _TABLAS:
        op.add_column(tabla, sa.Column("empresa_id", sa.Integer(), nullable=True))

    # Backfill. documents/gaps/query_logs → la (única) empresa por defecto.
    default_id = "(SELECT id FROM empresas ORDER BY id LIMIT 1)"
    op.execute(f"UPDATE documents SET empresa_id = {default_id}")
    op.execute(f"UPDATE gaps SET empresa_id = {default_id}")
    op.execute(f"UPDATE query_logs SET empresa_id = {default_id}")
    # chunks hereda la empresa de su documento.
    op.execute(
        "UPDATE chunks SET empresa_id = "
        "(SELECT documents.empresa_id FROM documents WHERE documents.id = chunks.doc_id)"
    )

    # FKs (CASCADE: borrar una empresa se lleva sus datos) + índice para el filtrado por
    # empresa en el retrieval.
    for tabla in _TABLAS:
        op.create_foreign_key(
            f"fk_{tabla}_empresa_id_empresas",
            tabla,
            "empresas",
            ["empresa_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{tabla}_empresa_id", tabla, ["empresa_id"])


def downgrade() -> None:
    for tabla in _TABLAS:
        op.drop_index(f"ix_{tabla}_empresa_id", table_name=tabla)
        op.drop_constraint(f"fk_{tabla}_empresa_id_empresas", tabla, type_="foreignkey")
        op.drop_column(tabla, "empresa_id")
    op.drop_table("empresas")
