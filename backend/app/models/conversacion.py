from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Conversacion(Base):
    """Hilo de chat persistente (Fase C).

    Pertenece a UN usuario dentro de UNA empresa: nadie ve las conversaciones de otro
    (aislamiento por usuario, además del de empresa). El `titulo` es el truncado del
    primer mensaje (sin LLM). `actualizada` se refresca en cada mensaje nuevo para poder
    ordenar la lista por actividad reciente.
    """

    __tablename__ = "conversaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    titulo: Mapped[str] = mapped_column(String(255))
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
