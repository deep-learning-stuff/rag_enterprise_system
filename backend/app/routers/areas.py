"""Panel de áreas (Fase B.5). Solo admin de empresa (superadmin no gestiona intra-empresa).

Todo queda acotado a la empresa del admin autenticado (`get_empresa_id_admin`): no puede
crear, ver ni renombrar áreas de otra empresa.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_empresa_id_admin
from app.schemas import AreaIn, AreaOut
from app.services import areas as service

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=list[AreaOut])
def list_areas(
    empresa_id: int = Depends(get_empresa_id_admin), db: Session = Depends(get_db)
) -> list[AreaOut]:
    return [AreaOut.model_validate(a) for a in service.list_areas(db, empresa_id)]


@router.post("", response_model=AreaOut, status_code=201)
def crear_area(
    body: AreaIn,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> AreaOut:
    try:
        area = service.crear_area(db, body.nombre, empresa_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AreaOut.model_validate(area)


@router.put("/{area_id}", response_model=AreaOut)
def renombrar_area(
    area_id: int,
    body: AreaIn,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> AreaOut:
    area = service.get_area(db, area_id, empresa_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    try:
        area = service.renombrar_area(db, area, body.nombre)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AreaOut.model_validate(area)
