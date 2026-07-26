"""Gestión de empresas (tenants). Solo el superadmin las crea/lista (ver router)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa


def crear_empresa(db: Session, nombre: str) -> Empresa:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la empresa no puede estar vacío.")
    if db.scalar(select(Empresa).where(Empresa.nombre == nombre)) is not None:
        raise ValueError("Ya existe una empresa con ese nombre.")
    empresa = Empresa(nombre=nombre)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


def list_empresas(db: Session) -> list[Empresa]:
    return list(db.scalars(select(Empresa).order_by(Empresa.nombre)))


def get_empresa(db: Session, empresa_id: int) -> Empresa | None:
    return db.get(Empresa, empresa_id)
