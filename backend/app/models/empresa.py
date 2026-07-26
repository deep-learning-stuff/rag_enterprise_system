from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Empresa(Base):
    """Empresa (tenant). Aísla documentos, chunks, gaps y consultas: una empresa NUNCA
    ve datos de otra.

    Este aislamiento es una invariante al nivel de las de grounding (ver CLAUDE.md) y se
    aplica en el retrieval (`hybrid_search` exige `empresa_id`), no solo en el modelo.
    """

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
