from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.empresa import Empresa


class Usuario(Base):
    """Usuario del sistema. Tres roles:

    - `superadmin`: opera la plataforma; ve y gestiona TODAS las empresas. `empresa_id` NULL
      (no está atado a ninguna empresa).
    - `admin`: gestiona los usuarios de SU empresa. `empresa_id` obligatorio.
    - `usuario`: solo pregunta al RAG de su empresa. `empresa_id` obligatorio.

    `password_hash` es NULL hasta que el usuario acepta su invitación y fija contraseña
    (ver modelo Invitacion). La coherencia rol<->empresa la garantiza un CHECK en BD, no
    solo el código.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
    empresa_id: Mapped[int | None] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # NULL hasta aceptar la invitación; entonces el usuario fija su propia contraseña.
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Cargada junto al usuario (joined) para poder mostrar el nombre de la empresa en el
    # branding sin una consulta extra ni lazy-load fuera de sesión. NULL en superadmin.
    empresa: Mapped["Empresa | None"] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "(rol = 'superadmin' AND empresa_id IS NULL) "
            "OR (rol IN ('admin', 'usuario') AND empresa_id IS NOT NULL)",
            name="ck_usuarios_rol_empresa",
        ),
    )

    @property
    def invitacion_pendiente(self) -> bool:
        """True si aún no aceptó la invitación (no tiene contraseña). Lo usa el panel
        para marcarlo y ofrecer 'reinvitar'."""
        return self.password_hash is None

    @property
    def empresa_nombre(self) -> str | None:
        """Nombre de la empresa del usuario (para el branding del frontend). NULL en
        superadmin, que no está atado a ninguna empresa."""
        return self.empresa.nombre if self.empresa else None
