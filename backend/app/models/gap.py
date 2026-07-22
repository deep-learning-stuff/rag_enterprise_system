from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db import Base


class Gap(Base):
    """Grupo de preguntas sin respuesta que son, en esencia, la misma pregunta.

    El agrupado es incremental (ver app.services.gaps): cada pregunta sin respuesta se
    compara por similitud coseno contra los gaps existentes; si se parece lo bastante a
    uno, se le suma (su embedding se actualiza como media móvil); si no, abre un gap
    nuevo. No hay reclustering por lotes a propósito: un gap es una fila estable en el
    tiempo, porque encima se pondrá estado editorial (fase de borradores).
    """

    __tablename__ = "gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    pregunta_representativa: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    n_ocurrencias: Mapped[int] = mapped_column(Integer, default=1)
    primera_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ultima_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
