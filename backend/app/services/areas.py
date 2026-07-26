"""Áreas/departamentos DENTRO de una empresa (Fase B.5).

Segundo nivel de acceso por debajo del tenant: el `admin` de empresa da de alta las
áreas y luego cuelga documentos (ver services.documents) y personas (ver
services.usuarios) de ellas. La AUTORIZACIÓN (que sea admin de la empresa) vive en el
router; aquí solo se garantiza el invariante de datos: el nombre es único DENTRO de la
empresa (lo respalda el `UniqueConstraint` empresa+nombre del modelo).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.area import Area


def crear_area(db: Session, nombre: str, empresa_id: int) -> Area:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del área no puede estar vacío.")
    if _existe_nombre(db, empresa_id, nombre):
        raise ValueError("Ya existe un área con ese nombre en la empresa.")
    area = Area(nombre=nombre, empresa_id=empresa_id)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def renombrar_area(db: Session, area: Area, nombre: str) -> Area:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del área no puede estar vacío.")
    if _existe_nombre(db, area.empresa_id, nombre, excluir_id=area.id):
        raise ValueError("Ya existe un área con ese nombre en la empresa.")
    area.nombre = nombre
    db.commit()
    db.refresh(area)
    return area


def list_areas(db: Session, empresa_id: int) -> list[Area]:
    return list(
        db.scalars(
            select(Area).where(Area.empresa_id == empresa_id).order_by(Area.nombre)
        )
    )


def get_area(db: Session, area_id: int, empresa_id: int) -> Area | None:
    """Área por id, SOLO si es de la empresa (aislamiento). Si no, None → 404 en el router."""
    area = db.get(Area, area_id)
    if area is None or area.empresa_id != empresa_id:
        return None
    return area


def _existe_nombre(
    db: Session, empresa_id: int, nombre: str, excluir_id: int | None = None
) -> bool:
    """True si ya hay un área con ese nombre en la empresa (opcionalmente ignorando una)."""
    q = select(Area.id).where(Area.empresa_id == empresa_id, Area.nombre == nombre)
    if excluir_id is not None:
        q = q.where(Area.id != excluir_id)
    return db.scalar(q) is not None
