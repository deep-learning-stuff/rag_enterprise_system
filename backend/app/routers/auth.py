from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas import AceptarInvitacionIn, LoginIn, UsuarioOut
from app.services import auth as auth_service
from app.services import usuarios as usuarios_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,  # inaccesible desde JS: mitiga robo por XSS
        samesite="lax",  # mitiga CSRF en las peticiones cross-site
        secure=settings.cookie_secure,  # solo HTTPS en producción
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/login", response_model=UsuarioOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UsuarioOut:
    """Valida credenciales, abre sesión y deja la cookie httpOnly."""
    usuario = auth_service.autenticar(db, body.email, body.password)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = auth_service.crear_sesion(db, usuario)
    _set_session_cookie(response, token)
    return UsuarioOut.model_validate(usuario)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    """Cierra la sesión: revoca en servidor y borra la cookie."""
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        auth_service.revocar_sesion(db, token)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)) -> UsuarioOut:
    """Usuario de la sesión actual (el frontend lo usa para saber rol y empresa)."""
    return UsuarioOut.model_validate(usuario)


@router.post("/aceptar-invitacion", response_model=UsuarioOut)
def aceptar_invitacion(body: AceptarInvitacionIn, db: Session = Depends(get_db)) -> UsuarioOut:
    """Público (el invitado aún no tiene sesión): fija la contraseña con el token del enlace."""
    try:
        usuario = usuarios_service.aceptar_invitacion(db, body.token, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UsuarioOut.model_validate(usuario)
