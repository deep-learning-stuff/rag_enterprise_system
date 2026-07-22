"""gaps: tabla de agrupado de preguntas sin respuesta + query_logs.gap_id

Revision ID: 0008_gaps
Revises: 500a35229882
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0008_gaps"
down_revision: Union[str, None] = "500a35229882"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pregunta_representativa", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("n_ocurrencias", sa.Integer(), nullable=False),
        sa.Column(
            "primera_vez", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "ultima_vez", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Índice HNSW para el nearest-neighbor del agrupado (mismo patrón que chunks.embedding).
    op.execute(
        "CREATE INDEX ix_gaps_embedding ON gaps USING hnsw (embedding vector_cosine_ops)"
    )

    op.add_column("query_logs", sa.Column("gap_id", sa.Integer(), nullable=True))
    op.create_index("ix_query_logs_gap_id", "query_logs", ["gap_id"])
    op.create_foreign_key(
        "fk_query_logs_gap_id_gaps",
        "query_logs",
        "gaps",
        ["gap_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_query_logs_gap_id_gaps", "query_logs", type_="foreignkey")
    op.drop_index("ix_query_logs_gap_id", table_name="query_logs")
    op.drop_column("query_logs", "gap_id")
    op.drop_index("ix_gaps_embedding", table_name="gaps")
    op.drop_table("gaps")
