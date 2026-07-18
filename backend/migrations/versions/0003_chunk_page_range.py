"""chunks: página única -> rango de páginas (page_start, page_end)

Revision ID: 0003_chunk_page_range
Revises: 0002_chunks
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_chunk_page_range"
down_revision: Union[str, None] = "0002_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("page_end", sa.Integer(), nullable=True))
    op.drop_column("chunks", "page")


def downgrade() -> None:
    op.add_column("chunks", sa.Column("page", sa.Integer(), nullable=True))
    op.drop_column("chunks", "page_end")
    op.drop_column("chunks", "page_start")
