"""Crea el superadmin inicial a partir de variables de entorno. Idempotente.

Es el arranque en frío del sistema de usuarios: sin un superadmin no hay quien cree
empresas ni usuarios. Se ejecuta UNA vez, a mano, para que la contraseña la teclee una
persona (no vive en ninguna migración ni en el código).

Uso (las variables van con -e para que lleguen AL CONTENEDOR; ponerlas delante no basta,
y en PowerShell esa sintaxis ni existe):
    docker compose run --rm --no-deps \
        -e SUPERADMIN_EMAIL=tu@correo -e SUPERADMIN_PASSWORD=... \
        backend python -m app.bootstrap_superadmin

Si ya existe un superadmin, no hace nada.
"""

import os
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.usuario import Usuario
from app.security import hash_password


def main() -> int:
    email = os.environ.get("SUPERADMIN_EMAIL")
    password = os.environ.get("SUPERADMIN_PASSWORD")
    nombre = os.environ.get("SUPERADMIN_NOMBRE", "Super Admin")

    if not email or not password:
        print("ERROR: define SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD en el entorno.")
        return 1
    if len(password) < 8:
        print("ERROR: la contraseña debe tener al menos 8 caracteres.")
        return 1

    email_norm = email.strip().lower()
    db = SessionLocal()
    try:
        existe = db.scalar(select(Usuario).where(Usuario.rol == "superadmin"))
        if existe is not None:
            print(f"Ya existe un superadmin ({existe.email}); no se crea otro.")
            return 0
        if db.scalar(select(Usuario).where(Usuario.email == email_norm)) is not None:
            print(f"ERROR: ya existe un usuario con email {email_norm}.")
            return 1

        db.add(
            Usuario(
                email=email_norm,
                nombre=nombre,
                rol="superadmin",
                empresa_id=None,
                password_hash=hash_password(password),
                activo=True,
            )
        )
        db.commit()
        print(f"Superadmin creado: {email_norm}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
