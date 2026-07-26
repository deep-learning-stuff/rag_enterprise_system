"""Dependencias transversales de FastAPI: identidad, empresa y guards de rol.

La identidad sale de la cookie de sesión (ver app.services.auth). La empresa YA NO viene
por cabecera: se deriva del usuario autenticado, que es la fuente de verdad del tenant.
"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.area import usuario_area
from app.models.usuario import Usuario
from app.services import auth as auth_service


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Usuario autenticado de la cookie de sesión. 401 si no hay sesión válida."""
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    usuario = auth_service.usuario_por_sesion(db, token)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return usuario


def get_empresa_id(usuario: Usuario = Depends(get_current_user)) -> int:
    """Empresa (tenant) del usuario autenticado. La usan los endpoints del RAG.

    Un superadmin no tiene empresa (empresa_id NULL): el RAG es por empresa, así que se
    le rechaza aquí en vez de dejarle recuperar de "ninguna" empresa.
    """
    if usuario.empresa_id is None:
        raise HTTPException(
            status_code=400,
            detail="Un superadmin no tiene empresa asociada; el RAG es por empresa.",
        )
    return usuario.empresa_id


def get_empresa_id_admin(usuario: Usuario = Depends(get_current_user)) -> int:
    """Empresa del usuario, exigiendo que sea ADMIN de empresa.

    Para acciones de gestión del RAG por empresa (ver/gestionar gaps, subir documentos):
    un `usuario` normal no puede (403); el superadmin tampoco (no tiene empresa).
    """
    if usuario.rol != "admin":
        raise HTTPException(status_code=403, detail="Requiere permisos de admin de empresa")
    if usuario.empresa_id is None:  # no debería pasar (CHECK en BD), defensivo
        raise HTTPException(status_code=400, detail="Admin sin empresa asociada")
    return usuario.empresa_id


def get_restriccion_areas(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[int] | None:
    """Áreas a las que se restringe el retrieval del usuario.

    - `admin`: None → sin restricción, ve todos los documentos de su empresa.
    - `usuario`: la lista de sus áreas → solo recupera de documentos que crucen con ellas
      (si no tiene ninguna, lista vacía → no ve nada).
    """
    if usuario.rol == "admin":
        return None
    return list(
        db.scalars(
            select(usuario_area.c.area_id).where(usuario_area.c.usuario_id == usuario.id)
        )
    )


def require_superadmin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Requiere permisos de superadmin")
    return usuario


def require_gestor(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """admin o superadmin: los que pueden gestionar usuarios (ver panel, Fase B paso 4)."""
    if usuario.rol not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Requiere permisos de admin")
    return usuario
