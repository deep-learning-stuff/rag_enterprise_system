"""chunks: columna embedding (vector 1024) + índice HNSW

Revision ID: 0004_chunk_embedding
Revises: 0003_chunk_page_range
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0004_chunk_embedding"
down_revision: Union[str, None] = "0003_chunk_page_range"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("embedding", Vector(1024), nullable=True))
    # Índice HNSW para búsqueda por similitud coseno (rápido en tablas grandes).
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding", table_name="chunks")
    op.drop_column("chunks", "embedding")
