"""gaps: marca de posible resolución por re-chequeo (posible_resuelto + resuelto_por_doc_id)

Revision ID: 0010_gap_recheck
Revises: 0009_gap_borrador
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010_gap_recheck"
down_revision: Union[str, None] = "0009_gap_borrador"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gaps",
        sa.Column(
            "posible_resuelto", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column("gaps", sa.Column("resuelto_por_doc_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_gaps_resuelto_por_doc_id_documents",
        "gaps",
        "documents",
        ["resuelto_por_doc_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_gaps_resuelto_por_doc_id_documents", "gaps", type_="foreignkey"
    )
    op.drop_column("gaps", "resuelto_por_doc_id")
    op.drop_column("gaps", "posible_resuelto")
