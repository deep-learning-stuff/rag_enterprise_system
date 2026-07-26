from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_superadmin
from app.models.usuario import Usuario
from app.schemas import EmpresaIn, EmpresaOut
from app.services import empresas as service

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.post("", response_model=EmpresaOut, status_code=201)
def crear_empresa(
    body: EmpresaIn,
    _: Usuario = Depends(require_superadmin),
    db: Session = Depends(get_db),
) -> EmpresaOut:
    """Da de alta una empresa. Solo superadmin."""
    try:
        empresa = service.crear_empresa(db, body.nombre)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EmpresaOut.model_validate(empresa)


@router.get("", response_model=list[EmpresaOut])
def list_empresas(
    _: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)
) -> list[EmpresaOut]:
    """Lista todas las empresas. Solo superadmin."""
    return [EmpresaOut.model_validate(e) for e in service.list_empresas(db)]
