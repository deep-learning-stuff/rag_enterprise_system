"""empresa_id -> NOT NULL en documents, chunks, gaps, query_logs

Revision ID: 0012_empresa_id_not_null
Revises: 0011_empresas
Create Date: 2026-07-26

Cierra la Fase A del multi-tenant: ahora TODOS los caminos de escritura (ingesta de
documentos, gaps, logs) sellan empresa_id, así que las columnas pasan a NOT NULL. Antes
del ALTER se hace un backfill defensivo (cualquier fila que hubiera quedado con
empresa_id NULL se asigna a la empresa por defecto / a la de su documento) para que el
ALTER no falle.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_empresa_id_not_null"
down_revision: Union[str, None] = "0011_empresas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLAS = ("documents", "chunks", "gaps", "query_logs")


def upgrade() -> None:
    # Backfill defensivo por si quedaran filas sin empresa (no debería, pero el ALTER a
    # NOT NULL fallaría si las hay).
    default_id = "(SELECT id FROM empresas ORDER BY id LIMIT 1)"
    op.execute(f"UPDATE documents SET empresa_id = {default_id} WHERE empresa_id IS NULL")
    op.execute(f"UPDATE gaps SET empresa_id = {default_id} WHERE empresa_id IS NULL")
    op.execute(f"UPDATE query_logs SET empresa_id = {default_id} WHERE empresa_id IS NULL")
    # chunks heredan de su documento; los huérfanos (sin doc) caen a la empresa por defecto.
    op.execute(
        "UPDATE chunks SET empresa_id = "
        "(SELECT documents.empresa_id FROM documents WHERE documents.id = chunks.doc_id) "
        "WHERE empresa_id IS NULL"
    )
    op.execute(f"UPDATE chunks SET empresa_id = {default_id} WHERE empresa_id IS NULL")

    for tabla in _TABLAS:
        op.alter_column(tabla, "empresa_id", nullable=False)


def downgrade() -> None:
    for tabla in _TABLAS:
        op.alter_column(tabla, "empresa_id", nullable=True)
