"""gaps: estado editorial + borrador + documento_id (ciclo de borradores)

Revision ID: 0009_gap_borrador
Revises: 0008_gaps
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_gap_borrador"
down_revision: Union[str, None] = "0008_gaps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `server_default` para que las filas de gaps ya existentes queden en "pendiente"
    # sin necesidad de backfill manual.
    op.add_column(
        "gaps",
        sa.Column(
            "estado", sa.String(length=20), nullable=False, server_default="pendiente"
        ),
    )
    op.add_column("gaps", sa.Column("borrador", sa.Text(), nullable=True))
    op.add_column("gaps", sa.Column("documento_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_gaps_documento_id_documents",
        "gaps",
        "documents",
        ["documento_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_gaps_documento_id_documents", "gaps", type_="foreignkey")
    op.drop_column("gaps", "documento_id")
    op.drop_column("gaps", "borrador")
    op.drop_column("gaps", "estado")
