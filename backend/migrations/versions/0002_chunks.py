"""chunks: tabla de trozos de documento

Revision ID: 0002_chunks
Revises: 0001_init
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_chunks"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "doc_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
    )
    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"])


def downgrade() -> None:
    op.drop_index("ix_chunks_doc_id", table_name="chunks")
    op.drop_table("chunks")
