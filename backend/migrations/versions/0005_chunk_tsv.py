"""chunks: columna tsv (full-text español) + índice GIN

Revision ID: 0005_chunk_tsv
Revises: 0004_chunk_embedding
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_chunk_tsv"
down_revision: Union[str, None] = "0004_chunk_embedding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columna generada: Postgres la mantiene sincronizada con `texto` automáticamente.
    op.execute(
        "ALTER TABLE chunks ADD COLUMN tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED"
    )
    # Índice GIN: el índice adecuado para búsqueda full-text sobre tsvector.
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv)")


def downgrade() -> None:
    op.drop_index("ix_chunks_tsv", table_name="chunks")
    op.drop_column("chunks", "tsv")
