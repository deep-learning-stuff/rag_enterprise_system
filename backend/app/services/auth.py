"""Autenticación: verificar credenciales y gestionar sesiones de servidor.

Una sesión es una fila en `sesiones` con el HASH del token (el valor en claro solo vive
en la cookie del navegador). Al estar en servidor, el logout borra la fila y la revoca
de verdad.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from app.security import generar_token, hash_token, verify_password


def autenticar(db: Session, email: str, password: str) -> Usuario | None:
    """Devuelve el usuario si email+contraseña son válidos y la cuenta está activa.

    Devuelve None (sin distinguir el motivo) si no existe, está inactivo, aún no ha
    aceptado la invitación (sin `password_hash`) o la contraseña no casa: no filtrar
    cuál de esas fue es intencionado.
    """
    email_norm = email.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.email == email_norm))
    if usuario is None or not usuario.activo or not usuario.password_hash:
        return None
    if not verify_password(password, usuario.password_hash):
        return None
    return usuario


def crear_sesion(db: Session, usuario: Usuario) -> str:
    """Crea una sesión para el usuario y devuelve el token en claro (va a la cookie)."""
    token = generar_token()
    expira = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(Sesion(usuario_id=usuario.id, token_hash=hash_token(token), expira=expira))
    db.commit()
    return token


def usuario_por_sesion(db: Session, token: str) -> Usuario | None:
    """Resuelve el usuario de una cookie de sesión, o None si no vale.

    None si el token no existe, la sesión caducó, o el usuario ya no está activo.
    """
    sesion = db.scalar(select(Sesion).where(Sesion.token_hash == hash_token(token)))
    if sesion is None or sesion.expira <= datetime.now(timezone.utc):
        return None
    usuario = db.get(Usuario, sesion.usuario_id)
    if usuario is None or not usuario.activo:
        return None
    return usuario


def revocar_sesion(db: Session, token: str) -> None:
    """Borra la sesión del token (logout): revocación real."""
    db.query(Sesion).filter(Sesion.token_hash == hash_token(token)).delete()
    db.commit()
