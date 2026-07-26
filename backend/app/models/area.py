from sqlalchemy import Column, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Area(Base):
    """Área/departamento DENTRO de una empresa (Contabilidad, RRHH, Legal…).

    Segundo nivel de acceso, por debajo de la empresa: un `usuario` ve los documentos
    cuyas áreas cruzan con las suyas (el "arnés" de cada persona). El `admin` de empresa
    ve todo, sin restricción por área. La relación con usuarios y documentos es N:M
    (un documento puede pertenecer a varias áreas y una persona a varias).
    """

    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_areas_empresa_nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(255))


# N:M usuario <-> área: las áreas a las que pertenece cada persona.
usuario_area = Table(
    "usuario_area",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("area_id", ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
)

# N:M documento <-> área: las áreas a las que pertenece cada documento.
documento_area = Table(
    "documento_area",
    Base.metadata,
    Column("documento_id", ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("area_id", ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
)
