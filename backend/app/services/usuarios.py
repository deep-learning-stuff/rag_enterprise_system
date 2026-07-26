"""Alta de usuarios por invitación y aceptación de la invitación.

El (super)admin crea el usuario SIN contraseña y se genera una invitación de un solo uso;
el usuario fija su propia contraseña al aceptarla. El token en claro solo se devuelve una
vez (para armar el enlace); en BD vive hasheado.

La AUTORIZACIÓN (quién puede crear a quién) NO vive aquí, sino en el router del panel
(Fase B paso 4). Aquí solo se garantizan las invariantes de datos.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.area import Area, usuario_area
from app.models.invitacion import Invitacion
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from app.security import generar_token, hash_password, hash_token

# Roles que se pueden crear por invitación (superadmin solo nace por bootstrap).
_ROLES_CREABLES = ("admin", "usuario")


def _nueva_invitacion(db: Session, usuario_id: int) -> str:
    """Crea una invitación para el usuario y devuelve el token en claro (no se persiste)."""
    token = generar_token()
    expira = datetime.now(timezone.utc) + timedelta(hours=settings.invite_ttl_hours)
    db.add(
        Invitacion(usuario_id=usuario_id, token_hash=hash_token(token), expira=expira)
    )
    return token


def _invalidar_pendientes(db: Session, usuario_id: int, ahora: datetime) -> None:
    """Marca como usadas las invitaciones pendientes del usuario (una a la vez válida)."""
    db.query(Invitacion).filter(
        Invitacion.usuario_id == usuario_id, Invitacion.usada_en.is_(None)
    ).update({Invitacion.usada_en: ahora})


def crear_usuario_con_invitacion(
    db: Session, *, email: str, nombre: str, rol: str, empresa_id: int
) -> tuple[Usuario, str]:
    """Crea un usuario sin contraseña + su invitación. Devuelve (usuario, token en claro)."""
    email_norm = email.strip().lower()
    if rol not in _ROLES_CREABLES:
        raise ValueError("Rol inválido: solo 'admin' o 'usuario'.")
    if db.scalar(select(Usuario).where(Usuario.email == email_norm)) is not None:
        raise ValueError("Ya existe un usuario con ese email.")

    usuario = Usuario(
        email=email_norm,
        nombre=nombre,
        rol=rol,
        empresa_id=empresa_id,
        password_hash=None,
        activo=True,
    )
    db.add(usuario)
    db.flush()  # necesitamos su id para la invitación
    token = _nueva_invitacion(db, usuario.id)
    db.commit()
    db.refresh(usuario)
    return usuario, token


def list_usuarios(db: Session, empresa_id: int | None = None) -> list[Usuario]:
    """Usuarios ordenados por empresa, rol y email.

    Si `empresa_id` es None devuelve TODOS (vista de superadmin, incluye superadmins con
    empresa NULL); si se pasa, solo los de esa empresa (vista de admin).
    """
    q = select(Usuario)
    if empresa_id is not None:
        q = q.where(Usuario.empresa_id == empresa_id)
    return list(db.scalars(q.order_by(Usuario.empresa_id, Usuario.rol, Usuario.email)))


def get_usuario(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def list_usuario_areas(db: Session, usuario: Usuario) -> list[Area]:
    """Áreas (el 'arnés') a las que pertenece el usuario, ordenadas por nombre."""
    return list(
        db.scalars(
            select(Area)
            .join(usuario_area, usuario_area.c.area_id == Area.id)
            .where(usuario_area.c.usuario_id == usuario.id)
            .order_by(Area.nombre)
        )
    )


def set_usuario_areas(
    db: Session, usuario: Usuario, area_ids: list[int], empresa_id: int
) -> list[Area]:
    """Reemplaza el conjunto de áreas del usuario.

    Todas las áreas deben ser de `empresa_id` (la del propio usuario; si no, sería una
    fuga entre empresas). La lista puede quedar vacía: un usuario sin áreas simplemente no
    ve ningún documento hasta que se le asigne alguna (estado válido, no un error).
    """
    ids = list(dict.fromkeys(area_ids))  # dedup conservando orden
    areas = (
        list(db.scalars(select(Area).where(Area.id.in_(ids), Area.empresa_id == empresa_id)))
        if ids
        else []
    )
    if len(areas) != len(ids):
        raise ValueError("Alguna área no existe o no pertenece a la empresa.")
    # Reemplazo directo sobre la tabla N:M (borra las actuales, inserta las nuevas): no
    # hay atributos en la relación, así que es más simple que cargar una relationship.
    db.execute(delete(usuario_area).where(usuario_area.c.usuario_id == usuario.id))
    if ids:
        db.execute(
            insert(usuario_area),
            [{"usuario_id": usuario.id, "area_id": aid} for aid in ids],
        )
    db.commit()
    return list_usuario_areas(db, usuario)


def set_activo(db: Session, usuario: Usuario, activo: bool) -> Usuario:
    """Activa o desactiva un usuario. Al desactivar, borra sus sesiones (lo echa ya).

    (Aunque no se borraran, `usuario_por_sesion` ya invalida la sesión de un inactivo;
    borrarlas es solo higiene y efecto inmediato.)
    """
    usuario.activo = activo
    if not activo:
        db.query(Sesion).filter(Sesion.usuario_id == usuario.id).delete()
    db.commit()
    db.refresh(usuario)
    return usuario


def regenerar_invitacion(db: Session, usuario: Usuario) -> str:
    """Reinvita: invalida las invitaciones pendientes y emite una nueva. Devuelve el token."""
    if usuario.password_hash is not None:
        raise ValueError("El usuario ya activó su cuenta; no necesita invitación.")
    _invalidar_pendientes(db, usuario.id, datetime.now(timezone.utc))
    token = _nueva_invitacion(db, usuario.id)
    db.commit()
    return token


def aceptar_invitacion(db: Session, token: str, password: str) -> Usuario:
    """Fija la contraseña del usuario a partir de una invitación válida.

    Falla (ValueError) si la invitación no existe, ya se usó o caducó, o si la contraseña
    es demasiado corta. Al aceptar, consume todas las invitaciones pendientes del usuario.
    """
    if len(password) < settings.password_min_length:
        raise ValueError(
            f"La contraseña debe tener al menos {settings.password_min_length} caracteres."
        )
    inv = db.scalar(select(Invitacion).where(Invitacion.token_hash == hash_token(token)))
    ahora = datetime.now(timezone.utc)
    if inv is None or inv.usada_en is not None or inv.expira <= ahora:
        raise ValueError("Invitación inválida, ya usada o caducada.")
    usuario = db.get(Usuario, inv.usuario_id)
    if usuario is None or not usuario.activo:
        raise ValueError("Invitación inválida.")

    usuario.password_hash = hash_password(password)
    _invalidar_pendientes(db, usuario.id, ahora)
    db.commit()
    db.refresh(usuario)
    return usuario
