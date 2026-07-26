"""Panel de gestión de usuarios.

Autorización por rol (los guards viven en app.deps; el scoping fino, aquí):
- superadmin: crea/ve usuarios en CUALQUIER empresa.
- admin: crea/ve usuarios SOLO en su empresa (rol admin o usuario).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_gestor
from app.models.usuario import Usuario
from app.schemas import (
    AreaOut,
    EnlaceInvitacionOut,
    UsuarioAreasIn,
    UsuarioCreadoOut,
    UsuarioCrearIn,
    UsuarioOut,
)
from app.services import empresas as empresas_service
from app.services import usuarios as service

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _enlace(token: str) -> str:
    """Ruta relativa de aceptación; el frontend le antepone su origin para el enlace final."""
    return f"/aceptar-invitacion?token={token}"


def _empresa_destino(actor: Usuario, empresa_id_body: int | None, db: Session) -> int:
    """Empresa en la que se creará el usuario, según el rol del que lo crea."""
    if actor.rol == "superadmin":
        if empresa_id_body is None:
            raise HTTPException(status_code=422, detail="empresa_id es obligatorio para superadmin")
        if empresas_service.get_empresa(db, empresa_id_body) is None:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return empresa_id_body
    # admin: siempre su propia empresa; pedir otra es un intento fuera de alcance.
    if empresa_id_body is not None and empresa_id_body != actor.empresa_id:
        raise HTTPException(status_code=403, detail="Un admin solo crea usuarios en su empresa")
    return actor.empresa_id


def _en_alcance(actor: Usuario, target: Usuario) -> bool:
    """True si `actor` puede gestionar a `target` (superadmin todo; admin solo su empresa)."""
    if actor.rol == "superadmin":
        return True
    return target.empresa_id == actor.empresa_id


@router.post("", response_model=UsuarioCreadoOut, status_code=201)
def crear_usuario(
    body: UsuarioCrearIn,
    actor: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
) -> UsuarioCreadoOut:
    """Crea un usuario (rol admin|usuario) y devuelve su enlace de invitación."""
    empresa_id = _empresa_destino(actor, body.empresa_id, db)
    try:
        usuario, token = service.crear_usuario_con_invitacion(
            db, email=body.email, nombre=body.nombre, rol=body.rol, empresa_id=empresa_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UsuarioCreadoOut(
        usuario=UsuarioOut.model_validate(usuario), enlace_invitacion=_enlace(token)
    )


@router.get("", response_model=list[UsuarioOut])
def list_usuarios(
    actor: Usuario = Depends(require_gestor), db: Session = Depends(get_db)
) -> list[UsuarioOut]:
    """Superadmin ve todos (agrupables por empresa en el front); admin, solo su empresa."""
    empresa_id = None if actor.rol == "superadmin" else actor.empresa_id
    return [UsuarioOut.model_validate(u) for u in service.list_usuarios(db, empresa_id)]


@router.post("/{usuario_id}/reinvitar", response_model=EnlaceInvitacionOut)
def reinvitar(
    usuario_id: int,
    actor: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
) -> EnlaceInvitacionOut:
    """Regenera la invitación de un usuario que aún no activó su cuenta."""
    target = service.get_usuario(db, usuario_id)
    if target is None or not _en_alcance(actor, target):
        # 404 (no 403) para no revelar la existencia de usuarios fuera de alcance.
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        token = service.regenerar_invitacion(db, target)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EnlaceInvitacionOut(enlace_invitacion=_enlace(token))


@router.post("/{usuario_id}/desactivar", response_model=UsuarioOut)
def desactivar(
    usuario_id: int,
    actor: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    """Desactiva un usuario (no podrá entrar y se le cierran las sesiones)."""
    target = service.get_usuario(db, usuario_id)
    if target is None or not _en_alcance(actor, target):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.id == actor.id:
        # Evita que alguien se autobloquee (garantiza que siempre queda quien lo hizo).
        raise HTTPException(status_code=409, detail="No puedes desactivarte a ti mismo")
    return UsuarioOut.model_validate(service.set_activo(db, target, False))


@router.post("/{usuario_id}/activar", response_model=UsuarioOut)
def activar(
    usuario_id: int,
    actor: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    """Reactiva un usuario desactivado."""
    target = service.get_usuario(db, usuario_id)
    if target is None or not _en_alcance(actor, target):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UsuarioOut.model_validate(service.set_activo(db, target, True))


@router.get("/{usuario_id}/areas", response_model=list[AreaOut])
def list_areas_usuario(
    usuario_id: int,
    actor: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
) -> list[AreaOut]:
    """Áreas asignadas a un usuario (su 'arnés' de acceso)."""
    target = service.get_usuario(db, usuario_id)
    if target is None or not _en_alcance(actor, target):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return [AreaOut.model_validate(a) for a in service.list_usuario_areas(db, target)]


@router.put("/{usuario_id}/areas", response_model=list[AreaOut])
def set_areas_usuario(
    usuario_id: int,
    body: UsuarioAreasIn,
    actor: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
) -> list[AreaOut]:
    """Reemplaza las áreas de un usuario. Las áreas deben ser de la empresa del usuario.

    Solo tiene efecto real en un `usuario` (el `admin` ve todo por rol); asignárselas a un
    admin es inocuo. Un superadmin no tiene empresa ni áreas → 400.
    """
    target = service.get_usuario(db, usuario_id)
    if target is None or not _en_alcance(actor, target):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.empresa_id is None:
        raise HTTPException(status_code=400, detail="Un superadmin no tiene áreas")
    try:
        areas = service.set_usuario_areas(db, target, body.area_ids, target.empresa_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [AreaOut.model_validate(a) for a in areas]
