from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Mensaje(Base):
    """Mensaje de una conversación (Fase C): del `usuario` o del `asistente`.

    - `usuario`: `texto` es la pregunta literal tal cual la escribió. `consulta_resuelta`
      guarda la versión autónoma con la que se recuperó, si hubo que reescribir un
      seguimiento (NULL si se usó el texto tal cual); sirve de transparencia y traza.
    - `asistente`: `texto` es la respuesta grounded (NULL si se abstuvo). `answered` y
      `reason` explican el resultado (mismos motivos que /answer, incl. `fuera_de_alcance`)
      y `citas` es la foto de los chunks citados (formato de SearchResultOut) para pintar
      las fuentes sin re-consultar.
    """

    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversacion_id: Mapped[int] = mapped_column(
        ForeignKey("conversaciones.id", ondelete="CASCADE"), index=True
    )
    rol: Mapped[str] = mapped_column(String(16))  # "usuario" | "asistente"
    texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    consulta_resuelta: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    citas: Mapped[list | None] = mapped_column(JSON, nullable=True)
    creado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
