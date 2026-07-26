"""usuarios, invitaciones y sesiones (Fase B: identidad y auth)

Revision ID: 0013_usuarios_auth
Revises: 0012_empresa_id_not_null
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0013_usuarios_auth"
down_revision: Union[str, None] = "0012_empresa_id_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        # Coherencia rol<->empresa: superadmin sin empresa; admin/usuario con empresa.
        sa.CheckConstraint(
            "(rol = 'superadmin' AND empresa_id IS NULL) "
            "OR (rol IN ('admin', 'usuario') AND empresa_id IS NOT NULL)",
            name="ck_usuarios_rol_empresa",
        ),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_index("ix_usuarios_empresa_id", "usuarios", ["empresa_id"])

    op.create_table(
        "invitaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_invitaciones_usuario_id", "invitaciones", ["usuario_id"])
    op.create_index(
        "ix_invitaciones_token_hash", "invitaciones", ["token_hash"], unique=True
    )

    op.create_table(
        "sesiones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sesiones_usuario_id", "sesiones", ["usuario_id"])
    op.create_index("ix_sesiones_token_hash", "sesiones", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("sesiones")
    op.drop_table("invitaciones")
    op.drop_table("usuarios")
