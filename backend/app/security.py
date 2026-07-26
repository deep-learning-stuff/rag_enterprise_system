"""Primitivas de seguridad: hashing de contraseñas y de tokens.

- Contraseñas: bcrypt (lento a propósito, con salt por hash).
- Tokens de invitación/sesión: son aleatorios de alta entropía, así que basta sha256
  (rápido) para guardarlos hasheados; no necesitan el coste de bcrypt.
"""

import hashlib
import secrets

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generar_token() -> str:
    """Token opaco aleatorio (para invitaciones y sesiones), seguro para URL."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash sha256 (hex, 64 chars) del token, que es lo único que se guarda en BD."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
